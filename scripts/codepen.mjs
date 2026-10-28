import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// Prints a CodePen "prefill" form payload (https://blog.codepen.io/documentation/prefill/)
// for the original (non-vendored) HTML source. CodePen v2 pens can import external
// URLs directly, so the source file is used rather than the vendored build.
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const { sources } = JSON.parse(await readFile(path.join(root, 'build.config.json'), 'utf8'));
const html = await readFile(path.join(root, sources[0]), 'utf8');
const data = JSON.stringify({ title: 'Video Overlay Animation Studio', html, editors: '100' });
const esc = (s) => s.replace(/&/g, '&amp;').replace(/'/g, '&apos;');
console.log(`<form action="https://codepen.io/pen/define" method="POST" target="_blank">
<input type="hidden" name="data" value='${esc(data)}'>
<input type="submit" value="Create CodePen">
</form>`);
