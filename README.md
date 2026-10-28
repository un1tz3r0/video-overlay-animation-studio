# Video Overlay Animation Studio

A single-file HTML application (`src/index.html`) wrapped in a build scaffold.
The build scans the sources for external fonts, images, stylesheets and
JavaScript modules, downloads ("vendors") them into `dist/vendor/`, copies the
sources to `dist/` and rewrites the links to relative paths. CSS `url()` /
`@import` and JS `import` chains are followed recursively.

Requires Node 18+; no npm dependencies.

## Usage

```sh
npm run build   # build into dist/
npm run dev     # build, then serve dist/ at https://localhost:8443 (PORT to override)
npm test
```

Add more sources in `build.config.json` (`sources`). The first source's
directory is the root of `dist/`.

The dev server generates a self-signed certificate on first run (needs the
`openssl` CLI) and caches it in `.devcert.pem` / `.devcert.key` (gitignored).
If `openssl` is missing it falls back to plain http. `dist/` is gitignored too.

## Publishing

All options publish the contents of `dist/`; run `npm run build` first.

- **GitHub Pages**: set Settings → Pages → Source to "GitHub Actions"; `.github/workflows/pages.yml`
  deploys on push to `main`. Or `npm run deploy:pages` to force-push `dist/` to a `gh-pages` branch.
- **Cloudflare Workers (static assets)**: edit `deploy/wrangler.toml`, `npx wrangler login`,
  then `npm run deploy:cloudflare`.
- **Google Cloud (App Engine)**: `gcloud auth login`, then
  `GCP_PROJECT=<id> npm run deploy:gcloud` (deploys `dist/` with `deploy/app.yaml`).
  For Cloud Storage instead: `gsutil -m rsync -r dist gs://<bucket>`.
- **CodePen (v2)**: `npm run codepen` writes `dist-codepen.html`, a prefill form that creates a new
  pen from the original source (CodePen resolves CDN imports itself). To update an existing pen,
  open it in CodePen v2 and paste in / sync `src/index.html`, or use the CodePen CLI/GitHub
  integration to sync the `src/` directory.
