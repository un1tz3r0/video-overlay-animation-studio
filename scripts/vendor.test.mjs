import test from 'node:test';
import assert from 'node:assert/strict';
import { createVendor } from './vendor.mjs';

const responses = {
  'https://fonts.googleapis.com/css2?family=X': ['text/css', '@font-face{src:url(https://fonts.gstatic.com/s/x.woff2)}'],
  'https://fonts.gstatic.com/s/x.woff2': ['font/woff2', 'FONT'],
  'https://cdn.example.com/lib.js': ['text/javascript', 'import d from "/dep.js";export default d'],
  'https://cdn.example.com/dep.js': ['text/javascript', 'export default 1'],
};
const fetchImpl = async (u) => {
  const r = responses[u]; if (!r) return { ok: false, status: 404 };
  return { ok: true, headers: { get: () => r[0] }, arrayBuffer: async () => Buffer.from(r[1]) };
};

test('vendors css, fonts, and js modules with relative paths', async () => {
  const v = createVendor({ outDir: 'x', vendorDir: 'vendor', fetchImpl });
  const out = await v.processHtml(`<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=X">
<script type="module">import l from "https://cdn.example.com/lib.js";</script>`, 'index.html');
  assert.doesNotMatch(out, /https:/);
  assert.match(out, /href="\.\/vendor\/fonts\.googleapis\.com\//);
  const css = [...v.files].find(([k]) => k.endsWith('.css'))[1].toString();
  assert.match(css, /url\("\.\.\/fonts\.gstatic\.com\//);
  const lib = [...v.files].find(([k]) => k.includes('lib.js'))[1].toString();
  assert.match(lib, /from "\.\/[0-9a-f]+-dep\.js"/);
});
