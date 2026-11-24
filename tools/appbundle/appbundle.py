#!/usr/bin/env python3
"""Package a web page and its assets into a one-file app that serves itself on localhost and opens a browser.

  python appbundle.py build page.html [SRC[=DEST] ...] [-n NAME] [-o DIR] [--icon FILE] [--windowed] [--vendor]
  python appbundle.py run   page.html [SRC[=DEST] ...] [-n NAME] [--vendor] [--port N] [--tab] [--no-browser] [--stay]

SRC is a file or folder; DEST is where it appears under the server root (default: its own name, "." for the root).
--vendor downloads the page's remote scripts, stylesheets and fonts, and everything they import, into /vendor/.
"""
import argparse, asyncio, contextlib, hashlib, html, json, mimetypes, os, platform, re, shutil, subprocess, sys, tempfile, webbrowser, zlib
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath

from aiohttp import ClientSession, ClientTimeout, web
from yarl import URL

# Windows reads these from the registry, where .js is sometimes text/plain, which breaks ES modules.
for ext, mime in {'.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css', '.json': 'application/json',
                  '.wasm': 'application/wasm', '.svg': 'image/svg+xml', '.mp4': 'video/mp4', '.webm': 'video/webm'}.items():
    mimetypes.add_type(mime, ext)

GRACE = 10
LIFELINE = b'<script>new EventSource("/__app/alive")</script>'
CHROMIUM = {
    'Windows': [rf'{root}\{app}' for root in ('%ProgramFiles%', '%ProgramFiles(x86)%', '%LocalAppData%')
                for app in (r'Google\Chrome\Application\chrome.exe', r'Microsoft\Edge\Application\msedge.exe',
                            r'BraveSoftware\Brave-Browser\Application\brave.exe')],
    'Darwin': [f'/Applications/{app}.app/Contents/MacOS/{app}' for app in ('Google Chrome', 'Microsoft Edge', 'Chromium', 'Brave Browser')],
    'Linux': ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser', 'microsoft-edge', 'brave-browser'],
}


def log(*msg):
    if sys.stderr:
        print(*msg, file=sys.stderr, flush=True)


def default_port(name):
    return 20000 + zlib.crc32(name.encode()) % 20000


def parse_mounts(specs):
    mounts = []
    for spec in specs:
        src, eq, dest = spec.rpartition('=')
        src, dest = (src, dest) if eq else (spec, None)
        src = Path(src).resolve()
        if not src.exists():
            sys.exit(f'appbundle: {src} does not exist')
        dest = PurePosixPath(src.name if dest is None else dest.replace('\\', '/').strip('/') or '.').as_posix()
        if dest == '.' and src.is_file():
            dest = src.name
        mounts.append(('' if dest == '.' else dest, src))
    return mounts


class PageRefs(HTMLParser):
    """External resources a page loads: (url, kind) pairs, the import map, and inline script and style text."""

    def __init__(self, text):
        super().__init__()
        self.refs, self.importmap, self.scripts, self.styles, self.open = [], {}, [], [], None
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        rel, as_ = set((a.get('rel') or '').lower().split()), a.get('as')
        kind = {'script': 'js', 'img': 'bin', 'source': 'bin', 'video': 'bin', 'audio': 'bin', 'track': 'bin'}.get(tag)
        if tag == 'link':
            kind = ('css' if 'stylesheet' in rel or as_ == 'style' else 'js' if 'modulepreload' in rel or as_ == 'script'
                    else 'bin' if rel & {'preload', 'icon', 'apple-touch-icon', 'manifest'} else None)
        if kind and (ref := a.get('href' if tag == 'link' else 'src')):
            self.refs.append((ref, kind))
        if tag in ('script', 'style') and not a.get('src'):
            self.open = (tag, a.get('type', ''), [])

    def handle_data(self, data):
        if self.open:
            self.open[2].append(data)

    def handle_endtag(self, tag):
        if not self.open or self.open[0] != tag:
            return
        _, kind, text = self.open
        text = ''.join(text)
        if kind == 'importmap':
            self.importmap = json.loads(text)
        elif tag == 'style':
            self.styles.append(text)
        elif kind in ('', 'module', 'text/javascript'):
            self.scripts.append(text)
        self.open = None


class Vendor:
    """Mirrors remote files under /vendor/<host>/<path> and points the references inside JS and CSS at the local copies.
    Bare specifiers stay bare, since the rewritten import map resolves them, but they are followed so their files get fetched."""

    UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'
    EXT = {'js': '.js', 'css': '.css'}
    JS = re.compile(r"""(\b(?:from|import)\s*|\bimport\s*\(\s*)(["'])([^"'\n]+?)\2"""
                    r"""|(\bnew\s+URL\s*\(\s*)(["'])([^"'\n]+?)\5(?=\s*,\s*import\.meta\.url)""")
    CSS = re.compile(r"""(@import\s+(?:url\(\s*)?|\burl\(\s*)(["']?)([^"')\s]+)\2""")
    REMOTE = re.compile(r'(https?:)?//')

    def __init__(self, session, root, imports):
        self.session, self.root, self.imports = session, root, imports
        self.tasks, self.failed, self.bytes = {}, [], 0

    @staticmethod
    def local(url, kind, prefix=False):
        path = re.sub(r'[<>:"\\|?*]', '_', url.path.lstrip('/'))
        if not prefix:
            path = path + 'index' if not path or path.endswith('/') else path
            if url.query_string:
                path += '-' + hashlib.sha1(url.query_string.encode()).hexdigest()[:10]
            if url.query_string or '.' not in path.rsplit('/', 1)[-1]:
                path += Vendor.EXT.get(kind, '')
        return f'/vendor/{url.host}/{path}'

    def resolve(self, base, spec):
        """(absolute URL, whether the reference gets rewritten) for a path or an import-mapped bare specifier, else None."""
        if re.match(r'(https?:)?//|\.{0,2}/', spec):
            return base.join(URL(spec)), True
        mapped = self.imports.get(spec) or next((v + spec[len(k):] for k, v in sorted(self.imports.items(), key=lambda kv: -len(kv[0]))
                                                 if k.endswith('/') and spec.startswith(k)), None)
        return (URL(mapped), False) if mapped and re.match(r'https?://', mapped) else None

    def want(self, url, kind, required=False):
        if str(url) not in self.tasks:
            self.tasks[str(url)] = asyncio.ensure_future(self.fetch(url, kind, required))
        return self.local(url, kind)

    def rewrite(self, base, text, pattern, kind_of):
        def sub(m):
            lead, quote, spec = (m[1], m[2], m[3]) if m[1] is not None else (m[4], m[5], m[6])
            found = None if spec.startswith('data:') else self.resolve(base, spec)
            if not found or found[0].scheme not in ('http', 'https'):
                return m[0]
            path = self.want(found[0], kind_of(lead))
            return f'{lead}{quote}{path}{quote}' if found[1] else m[0]
        return pattern.sub(sub, text)

    async def fetch(self, url, kind, required):
        try:
            async with self.session.get(url, headers={'User-Agent': self.UA}) as r:
                r.raise_for_status()
                body = await r.read()
        except Exception as e:
            self.failed.append((str(url), required, e))
            return
        if kind == 'js':
            body = self.rewrite(url, body.decode(), self.JS, lambda lead: 'bin' if lead.startswith('new') else 'js').encode()
        elif kind == 'css':
            body = self.rewrite(url, body.decode(), self.CSS, lambda lead: 'css' if lead.startswith('@import') else 'bin').encode()
        dest = self.root / self.local(url, kind).lstrip('/')
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(body)
        self.bytes += len(body)

    async def drain(self):
        while pending := [t for t in self.tasks.values() if not t.done()]:
            await asyncio.gather(*pending)


async def vendor_page(index, out):
    """Writes index, rewritten to use local copies of its remote resources, into out/, and the copies into out/vendor/."""
    text = index.read_text(encoding='utf-8')
    page = PageRefs(text)
    imports, swaps = page.importmap.get('imports', {}), {}
    remote = lambda ref: URL('https:' + ref if ref.startswith('//') else ref)
    async with ClientSession(trust_env=True, timeout=ClientTimeout(total=300)) as session:
        v = Vendor(session, out, imports)
        for ref, kind in page.refs:
            if v.REMOTE.match(ref):
                swaps[ref] = v.want(remote(ref), kind, required=True)
        for key, target in imports.items():
            if re.match(r'https?://', target):
                swaps[target] = v.local(URL(target), 'js', prefix=key.endswith('/'))
                if not key.endswith('/'):
                    v.want(URL(target), 'js', required=True)
        for code in page.scripts:
            for m in v.JS.finditer(code):
                spec = m[3] or m[6]
                if (v.REMOTE.match(spec) or spec in imports or any(k.endswith('/') and spec.startswith(k) for k in imports)) \
                        and (found := v.resolve(URL('https://page.invalid/'), spec)):
                    path = v.want(found[0], 'bin' if m[4] else 'js', required=True)
                    if found[1]:
                        swaps[spec] = path
        for css in page.styles:
            for m in v.CSS.finditer(css):
                if v.REMOTE.match(m[3]):
                    swaps[m[3]] = v.want(remote(m[3]), 'css' if m[1].startswith('@import') else 'bin', required=True)
        await v.drain()
    if errors := [f'  {url}: {e}' for url, required, e in v.failed if required]:
        sys.exit('appbundle: could not vendor\n' + '\n'.join(errors))
    for url, _, e in v.failed:
        log(f'appbundle: skipped {url} ({e})')
    for old, new in sorted(swaps.items(), key=lambda kv: -len(kv[0])):
        text = text.replace(html.escape(old), new).replace(old, new)
    (out / index.name).write_text(text, encoding='utf-8')
    hosts = ', '.join(sorted({URL(u).host for u in v.tasks}))
    log(f'Vendored {len(v.tasks) - len(v.failed)} files ({v.bytes / 1e6:.1f} MB) from {hosts}')
    return out / index.name


def open_browser(url, tab):
    exe = None if tab else next(filter(None, (shutil.which(os.path.expandvars(c)) for c in CHROMIUM.get(platform.system(), []))), None)
    if exe:
        subprocess.Popen([exe, f'--app={url}'], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
    else:
        webbrowser.open(str(url))


async def already_running(url, app_id):
    try:
        async with ClientSession(timeout=ClientTimeout(total=1)) as s, s.get(url / '__app/id') as r:
            return (await r.json()).get('id') == app_id
    except Exception:
        return False


async def serve(cfg, index, mounts, opts):
    port = opts.port or cfg['port']
    url = URL.build(scheme='http', host='127.0.0.1', port=port)
    if await already_running(url, cfg['name']):
        log(f'{cfg["name"]} is already running at {url}')
        if not opts.no_browser:
            open_browser(url, opts.tab)
        return

    html = index.read_bytes()
    at = html.lower().find(b'</head>')
    page = html[:at] + LIFELINE + html[at:] if at >= 0 else LIFELINE + html
    alive, done, loop = set(), asyncio.Event(), asyncio.get_running_loop()

    @web.middleware
    async def local_only(request, handler):
        if request.host not in {f'127.0.0.1:{port}', f'localhost:{port}'}:
            raise web.HTTPMisdirectedRequest()
        return await handler(request)

    async def lifeline(request):
        resp = web.StreamResponse(headers={'Content-Type': 'text/event-stream', 'Cache-Control': 'no-store'})
        await resp.prepare(request)
        me = object()
        alive.add(me)
        try:
            while True:
                await resp.write(b': ping\n\n')
                await asyncio.sleep(2)
        except ConnectionError:
            return resp
        finally:
            alive.discard(me)
            if not alive and not opts.stay:
                loop.call_later(GRACE, lambda: alive or done.set())

    async def app_id(_):
        return web.json_response({'id': cfg['name']})

    async def index_page(_):
        return web.Response(body=page, content_type='text/html', charset='utf-8', headers={'Cache-Control': 'no-store'})

    app = web.Application(middlewares=[local_only])
    app.router.add_get('/__app/alive', lifeline)
    app.router.add_get('/__app/id', app_id)
    app.router.add_get('/', index_page)
    app.router.add_get(f'/{index.name}', index_page)
    for dest, src in sorted(mounts, key=lambda m: -len(m[0])):
        if src.is_dir():
            app.router.add_static(f'/{dest}', src)
        else:
            app.router.add_get(f'/{dest}', file_handler(src))

    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    try:
        try:
            await web.TCPSite(runner, '127.0.0.1', port).start()
        except OSError:
            log(f'Port {port} is taken, using a random one. Browser storage (settings, file handles) is per port, so it will not carry over.')
            await web.TCPSite(runner, '127.0.0.1', 0).start()
            port = runner.addresses[0][1]
            url = url.with_port(port)
        log(f'{cfg["name"]} is serving at {url}' + ('' if opts.stay else ' and exits when its last window closes'))
        if not opts.no_browser:
            open_browser(url, opts.tab)
            if not opts.stay:
                loop.call_later(60, lambda: alive or done.set())
        await done.wait()
    finally:
        await runner.cleanup()


def file_handler(src):
    async def handler(_):
        return web.FileResponse(src)
    return handler


def launch_options(parser):
    parser.add_argument('--port', type=int, help='port to serve on (default: derived from the app name, so browser storage persists)')
    parser.add_argument('--tab', action='store_true', help='open a tab in the default browser instead of a Chromium app window')
    parser.add_argument('--no-browser', action='store_true', help='only start the server')
    parser.add_argument('--stay', action='store_true', help='keep serving after the last window closes')
    return parser


def build(args):
    index, mounts = Path(args.html).resolve(), parse_mounts(args.assets)
    name = args.name or index.stem.replace('-', ' ').replace('_', ' ').title()
    slug = ''.join(c if c.isalnum() else '-' for c in name).strip('-').lower()
    mode = ['--onedir' if args.windowed and platform.system() == 'Darwin' else '--onefile', *(['--windowed'] if args.windowed else [])]
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        site = tmp / 'site'
        site.mkdir()
        shutil.copy2(index, site / index.name)
        if args.vendor:
            asyncio.run(vendor_page(index, site))
        for dest, src in mounts:
            if src.is_dir():
                shutil.copytree(src, site / dest, dirs_exist_ok=True)
            else:
                (site / dest).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, site / dest)
        (tmp / 'app.json').write_text(json.dumps({'name': name, 'index': index.name, 'port': args.port or default_port(name)}))
        subprocess.run([
            sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--log-level', 'WARN', '--name', slug,
            *mode, *(['--icon', str(Path(args.icon).resolve())] if args.icon else []),
            '--distpath', str(Path(args.out).resolve()), '--workpath', str(tmp / 'work'), '--specpath', str(tmp),
            '--add-data', f'{site}{os.pathsep}site', '--add-data', f'{tmp / "app.json"}{os.pathsep}.', str(Path(__file__).resolve()),
        ], check=True)
    log(f'Built {Path(args.out) / slug}')


def main():
    if getattr(sys, 'frozen', False):
        root = Path(sys._MEIPASS)
        cfg = json.loads((root / 'app.json').read_text())
        opts = launch_options(argparse.ArgumentParser(prog=cfg['name'])).parse_args()
        return asyncio.run(serve(cfg, root / 'site' / cfg['index'], [('', root / 'site')], opts))

    cli = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = cli.add_subparsers(dest='cmd', required=True)
    for cmd in ('build', 'run'):
        p = sub.add_parser(cmd)
        p.add_argument('html', help='the page served at /')
        p.add_argument('assets', nargs='*', metavar='SRC[=DEST]', help='extra files or folders to serve')
        p.add_argument('-n', '--name', help='app name (default: from the HTML file name)')
        p.add_argument('--vendor', action='store_true', help='download remote scripts, styles and fonts so the app works offline')
    b = sub.choices['build']
    b.add_argument('-o', '--out', default='dist', help='output folder (default: dist)')
    b.add_argument('--icon', help='app icon (.ico, .icns, or .png when Pillow is installed)')
    b.add_argument('--windowed', action='store_true', help='no console window (a .app bundle on macOS)')
    b.add_argument('--port', type=int, help='fixed port baked into the app')
    launch_options(sub.choices['run'])
    args = cli.parse_args()
    if args.cmd == 'build':
        return build(args)
    index, mounts = Path(args.html).resolve(), parse_mounts(args.assets)
    name = args.name or index.stem
    with tempfile.TemporaryDirectory() as tmp:
        if args.vendor:
            index = asyncio.run(vendor_page(index, Path(tmp)))
            mounts.append(('vendor', Path(tmp) / 'vendor'))
        asyncio.run(serve({'name': name, 'port': default_port(name)}, index, mounts, args))


if __name__ == '__main__':
    with contextlib.suppress(KeyboardInterrupt):
        main()
