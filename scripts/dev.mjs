import http from 'node:http';
import https from 'node:https';
import { createReadStream, existsSync, statSync } from 'node:fs';
import { readFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { build } from './build.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const certFile = path.join(root, '.devcert.pem');
const keyFile = path.join(root, '.devcert.key');
const port = Number(process.env.PORT || 8443);
const types = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css',
  '.json': 'application/json', '.woff2': 'font/woff2', '.woff': 'font/woff', '.ttf': 'font/ttf',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml', '.webp': 'image/webp' };

function ensureCert() {
  if (!existsSync(certFile) || !existsSync(keyFile)) {
    execFileSync('openssl', ['req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '365', '-subj', '/CN=localhost',
      '-addext', 'subjectAltName=DNS:localhost,IP:127.0.0.1', '-keyout', keyFile, '-out', certFile], { stdio: 'ignore' });
  }
  return { cert: readFileSync(certFile), key: readFileSync(keyFile) };
}

const outDir = await build();

const handler = (req, res) => {
  let p = decodeURIComponent(new URL(req.url, 'http://x').pathname);
  let file = path.join(outDir, path.normalize(p));
  if (file !== outDir && !file.startsWith(outDir + path.sep)) { res.writeHead(403).end(); return; }
  if (existsSync(file) && statSync(file).isDirectory()) file = path.join(file, 'index.html');
  if (!existsSync(file)) { res.writeHead(404).end('Not found'); return; }
  res.writeHead(200, { 'Content-Type': types[path.extname(file)] || 'application/octet-stream' });
  createReadStream(file).pipe(res);
};

let server, scheme = 'https';
try {
  server = https.createServer(ensureCert(), handler);
} catch (e) {
  console.warn('Could not generate self-signed cert (is openssl installed?); falling back to http.');
  server = http.createServer(handler); scheme = 'http';
}
server.listen(port, () => console.log(`Serving ${outDir} at ${scheme}://localhost:${port}/`));
