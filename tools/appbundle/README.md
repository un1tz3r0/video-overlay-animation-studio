# appbundle

A standalone Python tool, kept here to package Overlay Studio as a desktop app (see
[docs/INSTALL.desktop.md](../../docs/INSTALL.desktop.md)). It packs a web page and its assets into one executable. When you run it, it serves the files on `127.0.0.1` and opens them in a Chromium app window (Chrome, Edge or Brave), falling back to the default browser. It exits when the last window closes.

## Setup

```sh
pip install aiohttp yarl pyinstaller
```

## Usage

From the repository root:

```sh
# package the vendored build (what `npm run package:desktop` runs after `npm run build`)
python3 tools/appbundle/appbundle.py build dist/index.html dist/vendor -n "Overlay Studio" --windowed -o dist-desktop

# try it without packaging
python3 tools/appbundle/appbundle.py run dist/index.html dist/vendor -n "Overlay Studio"

# or skip the Node build and let appbundle vendor the source itself
python3 tools/appbundle/appbundle.py build src/index.html -n "Overlay Studio" --vendor --windowed -o dist-desktop

# add your own files and folders
python3 tools/appbundle/appbundle.py build game.html sprites levels/1.json=data/level1.json --vendor
```

`build` writes to `dist/` unless given `-o`; use `-o dist-desktop` here so it doesn't overwrite the
web build.

Each extra argument is `SRC[=DEST]`. SRC is a file or folder. DEST is its path under the server root, which defaults to SRC's own name; use `.` to merge a folder into the root. The HTML file is served at `/` and under its own name.

The packaged app accepts `--port N`, `--tab` (use a normal browser tab), `--no-browser` and `--stay` (keep serving after the window closes). `run` accepts the same flags.

## Vendoring

`--vendor` makes the app work offline. At build time it downloads every remote resource the page loads, and everything those resources load in turn, into `/vendor/<host>/<path>`. Then it rewrites the page to use the local copies.

- **What it finds in the page:** `<script src>`, stylesheet, preload and icon `<link>`s, media `src`s, import-map entries (including prefix entries like `"three/addons/"`), static and dynamic imports in inline scripts, and `@import`/`url()` in inline styles.
- **What it follows in JS and CSS:** `import`/`export … from`, `import()`, and `new URL('…', import.meta.url)` in JS; `@import` and `url()` in CSS. References get rewritten to the local paths. Bare specifiers are left for the import map.
- **Fonts:** Google Fonts serves different CSS per browser, so it fetches as current Chrome and gets the woff2 files with their unicode-range subsets.
- **Failures:** if a file the page itself references can't be fetched, the build stops. Anything only found inside a downloaded file is skipped with a warning, since a regex match there can be a false positive.

It can't see URLs built at runtime, such as `import(someVariable)`, `fetch()` calls or worker scripts set by a library at run time. Those still go to the network, or need to be passed as assets. `run --vendor` lets you check a page before building.

## How it behaves

- **Stable origin.** The port is derived from the app name, so `localStorage`, IndexedDB and saved file handles survive restarts. Renaming the app changes the port and starts with empty storage. If the port is taken by something else, the app uses a random port and warns you.
- **Single instance.** Launching it again while it is running opens another window on the running server.
- **Exit on close.** A one-line `EventSource` is injected into the page. The server exits 10 s after the last connection drops, which leaves time for a reload. It also exits after 60 s if no window ever connects.
- **Local only.** It binds `127.0.0.1` and refuses requests whose `Host` header isn't `127.0.0.1` or `localhost`, which blocks DNS-rebinding pages from reading it.
- **Secure context.** `http://127.0.0.1` counts as secure, so WebCodecs, File System Access and the other secure-context APIs work.

## Building for every OS

PyInstaller only builds for the OS it runs on. To get all three, use CI. A GitHub Actions matrix like this produces Linux, Windows and macOS builds:

```yaml
name: build
on: workflow_dispatch
jobs:
  build:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 22 }
      - uses: actions/setup-python@v5
        with: { python-version: '3.13' }
      - run: pip install aiohttp yarl pyinstaller
      - run: npm run build
      - run: python tools/appbundle/appbundle.py build dist/index.html dist/vendor -n "Overlay Studio" --windowed -o dist-desktop
      - uses: actions/upload-artifact@v4
        with: { name: 'overlay-studio-${{ runner.os }}', path: dist-desktop/ }
```

`macos-latest` is Apple Silicon; add `macos-13` for an Intel build.

## Caveats

- **Unsigned binaries.** On macOS, Gatekeeper blocks the first launch: right-click it and choose Open, or run `xattr -d com.apple.quarantine`. On Windows, SmartScreen asks you to confirm with More info, then Run anyway. Signing removes both prompts but needs a paid certificate.
- **Offline.** Without `--vendor`, the app is only as offline as the page, so CDN imports and fonts still need the network.
- **Licenses.** Vendoring redistributes the downloaded files. three.js and Mediabunny (MIT) and Google Fonts (OFL or Apache) all allow that, but check anything else you pull in.
- **One-file startup.** One-file builds unpack to a temp folder on every launch. That is quick for a few MB but noticeable for hundreds. On macOS, `--windowed` makes a `.app` bundle, which unpacks nothing.
