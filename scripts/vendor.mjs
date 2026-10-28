import { createHash } from 'node:crypto';
import path from 'node:path';

const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36';
const isRemote = (u) => /^(https?:)?\/\//i.test(u);
const abs = (u) => (u.startsWith('//') ? 'https:' + u : u);

// Returns [{start, end, url}] style rewrites via a replacer callback.
export function rewriteHtml(html, fn) {
  const attr = (tagRe, attrName, test) => {
    html = html.replace(tagRe, (tag) =>
      test && !test(tag) ? tag : tag.replace(new RegExp(`(\\s${attrName}\\s*=\\s*)(["'])(.*?)\\2`, 'i'),
        (m, pre, q, v) => (isRemote(v) ? `${pre}${q}\u0000${v}\u0001${q}` : m)));
  };
  attr(/<script\b[^>]*>/gi, 'src');
  attr(/<img\b[^>]*>/gi, 'src');
  attr(/<(?:source|video|audio)\b[^>]*>/gi, 'src');
  attr(/<link\b[^>]*>/gi, 'href', (t) => /rel\s*=\s*["']?(stylesheet|icon|shortcut icon|apple-touch-icon|modulepreload)/i.test(t) ||
    /rel\s*=\s*["']?preload/i.test(t) && /as\s*=\s*["']?(font|style|script|image)/i.test(t));
  return html;
}

export function createVendor({ outDir, vendorDir, fetchImpl = fetch, log = () => {} }) {
  const cache = new Map(); // url -> output path relative to outDir (posix)
  const files = new Map(); // rel path -> Buffer

  function localName(url, contentType = '') {
    const u = new URL(url);
    let base = path.posix.basename(u.pathname) || 'index';
    base = base.replace(/[^\w.\-+]/g, '_');
    if (!path.posix.extname(base)) {
      if (/css/.test(contentType) || /fonts\.googleapis/.test(u.host)) base += '.css';
      else if (/javascript/.test(contentType)) base += '.js';
    }
    const hash = createHash('sha1').update(url).digest('hex').slice(0, 8);
    return path.posix.join(vendorDir, u.host.replace(/[^\w.-]/g, '_'), `${hash}-${base}`);
  }

  async function fetchAsset(url) {
    const res = await fetchImpl(url, { headers: { 'User-Agent': UA } });
    if (!res.ok) throw new Error(`GET ${url} -> ${res.status}`);
    return { buf: Buffer.from(await res.arrayBuffer()), type: res.headers.get('content-type') || '' };
  }

  const relFrom = (fromRel, toRel) => {
    const r = path.posix.relative(path.posix.dirname(fromRel), toRel);
    return r.startsWith('.') ? r : './' + r;
  };

  // Vendor `url`, returns its path relative to outDir. `kind` is a hint: css|js|other
  async function vendor(url) {
    url = abs(url);
    if (cache.has(url)) return cache.get(url);
    const { buf, type } = await fetchAsset(url);
    const rel = localName(url, type);
    cache.set(url, rel);
    log(`vendored ${url} -> ${rel}`);
    let out = buf;
    const isCss = /css/.test(type) || rel.endsWith('.css');
    const isJs = /javascript/.test(type) || /\.m?js$/.test(rel);
    if (isCss) out = Buffer.from(await rewriteCss(buf.toString('utf8'), url, rel));
    else if (isJs) out = Buffer.from(await rewriteJs(buf.toString('utf8'), url, rel));
    files.set(rel, out);
    return rel;
  }

  async function replaceAsync(str, re, fn) {
    const parts = []; let last = 0, m;
    re.lastIndex = 0;
    while ((m = re.exec(str))) { parts.push(str.slice(last, m.index), fn(...m)); last = m.index + m[0].length; }
    parts.push(str.slice(last));
    const done = await Promise.all(parts);
    return done.join('');
  }

  const resolveUrl = (ref, base) => { try { return new URL(ref, base).href; } catch { return null; } };

  async function rewriteCss(css, baseUrl, fromRel) {
    const re = /url\(\s*(['"]?)([^'")]+)\1\s*\)|@import\s+(['"])([^'"]+)\3/g;
    return replaceAsync(css, re, async (m, q, u, q2, imp) => {
      const ref = u || imp;
      if (/^(data:|#)/.test(ref)) return m;
      const full = resolveUrl(ref, baseUrl);
      if (!full || !/^https?:/.test(full)) return m;
      const rel = relFrom(fromRel, await vendor(full));
      return u ? `url("${rel}")` : `@import "${rel}"`;
    });
  }

  async function rewriteJs(js, baseUrl, fromRel) {
    const re = /(\b(?:import|export)\s*(?:[^'"()]*?\bfrom\s*)?|\bimport\s*\(\s*)(["'])([^"']+)\2/g;
    return replaceAsync(js, re, async (m, pre, q, spec) => {
      if (!/^(https?:|\/|\.\.?\/)/.test(spec)) return m;
      const full = resolveUrl(spec, baseUrl);
      if (!full || !/^https?:/.test(full)) return m;
      return `${pre}${q}${relFrom(fromRel, await vendor(full))}${q}`;
    });
  }

  // Process a full HTML document located at `htmlRel` inside outDir.
  async function processHtml(html, htmlRel) {
    const marked = rewriteHtml(html, null);
    // remote src/href attribute values
    let out = await replaceAsync(marked, /\u0000(.*?)\u0001/g, async (m, url) =>
      relFrom(htmlRel, await vendor(url)));
    // inline <style> blocks and inline module scripts
    out = await replaceAsync(out, /(<style\b[^>]*>)([\s\S]*?)(<\/style>)/gi, async (m, a, body, c) =>
      a + await rewriteCssInline(body, htmlRel) + c);
    out = await replaceAsync(out, /(<script\b(?![^>]*\bsrc=)[^>]*>)([\s\S]*?)(<\/script>)/gi, async (m, a, body, c) =>
      /type\s*=\s*["']?module/i.test(a) ? a + await rewriteInlineJs(body, htmlRel) + c : m);
    return out;
  }

  const rewriteCssInline = (css, htmlRel) => rewriteCssRemoteOnly(css, htmlRel);
  async function rewriteCssRemoteOnly(css, htmlRel) {
    return rewriteCss(css, 'https://invalid.local/', htmlRel);
  }
  async function rewriteInlineJs(js, htmlRel) {
    return rewriteJs(js, 'https://invalid.local/', htmlRel);
  }

  return { vendor, processHtml, files, cache };
}
