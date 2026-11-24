# Building

`src/index.html` runs as is: open it in a browser and it loads three.js, Mediabunny and its fonts
from their CDNs. The build makes a copy in `dist/` that needs no network.

Requires Node 18+. There are no npm dependencies, so there is nothing to install.

```sh
npm run build   # src/ -> dist/
npm run dev     # build, then serve dist/ at https://localhost:8443 (PORT to override)
npm test        # vendorer unit tests
```

## What the build does

`scripts/build.mjs` reads `build.config.json`, copies each source into `dist/`, and passes HTML
through the vendorer in `scripts/vendor.mjs`. The vendorer finds every remote reference, downloads
it into `dist/vendor/<host>/`, and rewrites the reference to a relative path:

- `<script src>`, `<link href>` (stylesheets, preloads, icons) and media `src`s
- `<script type="importmap">` entries; prefix mappings ending in `/` are left alone
- `import` and `export … from` in inline module scripts and in every downloaded JS file
- `@import` and `url()` in inline styles and in every downloaded stylesheet

It follows those chains recursively, so `three.module.js` brings `three.core.js` with it, and the
Google Fonts stylesheet brings its `woff2` files. Each URL is fetched once.

```
dist/
├── index.html
└── vendor/
    ├── cdn.jsdelivr.net/        three.module.js, three.core.js, mediabunny.min.mjs
    ├── fonts.googleapis.com/    css2.css
    └── fonts.gstatic.com/       *.woff2
```

Vendored names get a short hash prefix, so two URLs with the same file name never collide.

## Configuration

`build.config.json`:

| Key | Default | Meaning |
| --- | --- | --- |
| `sources` | | Files to build. The first one's directory is the root of `dist/`. |
| `outDir` | `dist` | Output folder; emptied on every build. |
| `vendorDir` | `vendor` | Folder under `outDir` for downloaded files. |

## Behind a proxy

Node's `fetch` ignores `HTTPS_PROXY` unless told otherwise. On Node 22.13+ or 23.4+:

```sh
NODE_USE_ENV_PROXY=1 NODE_EXTRA_CA_CERTS=/path/to/proxy-ca.pem npm run build
```

`NODE_EXTRA_CA_CERTS` is only needed when the proxy re-signs TLS with its own CA.

## Dev server

`npm run dev` generates a self-signed certificate on first run with the `openssl` CLI and caches it
in `.devcert.pem` / `.devcert.key`. HTTPS keeps the secure-context APIs (WebCodecs, File System
Access, OPFS) working when you open the page from another machine on your network. Without
`openssl` it falls back to plain HTTP, which still counts as secure on `localhost`.

## Packaging

`npm run package:desktop` builds and wraps `dist/` in a desktop app. See
[INSTALL.desktop.md](INSTALL.desktop.md).
