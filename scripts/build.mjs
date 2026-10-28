import { readFile, writeFile, mkdir, rm } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createVendor } from './vendor.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

export async function build({ quiet = false } = {}) {
  const config = JSON.parse(await readFile(path.join(root, 'build.config.json'), 'utf8'));
  const outDir = path.join(root, config.outDir || 'dist');
  const vendorDir = config.vendorDir || 'vendor';
  await rm(outDir, { recursive: true, force: true });
  await mkdir(outDir, { recursive: true });

  const v = createVendor({ outDir, vendorDir, log: (m) => !quiet && console.log(m) });
  const srcRoot = path.join(root, path.dirname(config.sources[0]));
  for (const src of config.sources) {
    const rel = path.relative(srcRoot, path.join(root, src)).split(path.sep).join('/');
    let data = await readFile(path.join(root, src));
    if (/\.html?$/i.test(src)) data = Buffer.from(await v.processHtml(data.toString('utf8'), rel));
    const dest = path.join(outDir, rel);
    await mkdir(path.dirname(dest), { recursive: true });
    await writeFile(dest, data);
    if (!quiet) console.log(`built ${src} -> ${path.relative(root, dest)}`);
  }
  for (const [rel, buf] of v.files) {
    const dest = path.join(outDir, rel);
    await mkdir(path.dirname(dest), { recursive: true });
    await writeFile(dest, buf);
  }
  return outDir;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  build().catch((e) => { console.error(e); process.exit(1); });
}
