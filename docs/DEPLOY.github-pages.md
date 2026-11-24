# Deploying to GitHub Pages

## With Actions (recommended)

1. In the repository, open **Settings → Pages** and set **Source** to **GitHub Actions**.
2. Push to `main`, or run the workflow by hand from the **Actions** tab.

`.github/workflows/pages.yml` checks out the repo, runs `npm run build` on Node 22 and publishes
`dist/`. The site appears at `https://<user>.github.io/<repo>/`. Because every vendored path is
relative, it works from that sub-path with no base URL setting.

## By hand

```sh
npm run deploy:pages
```

This builds `dist/`, commits it to a fresh `gh-pages` branch and force-pushes it to `origin`. Set
**Settings → Pages → Source** to **Deploy from a branch**, branch `gh-pages`, folder `/`.
