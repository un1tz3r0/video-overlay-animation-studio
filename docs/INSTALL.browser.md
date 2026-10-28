# Running in the browser

Overlay Studio needs no install. Pick whichever fits:

- **Hosted.** Open the deployed copy, for example the GitHub Pages site
  (see [DEPLOY.github-pages.md](DEPLOY.github-pages.md)).
- **From the source file.** Open `src/index.html` straight from disk. It loads three.js, Mediabunny
  and fonts from their CDNs, so it needs the network.
- **Offline.** `npm run dev` builds `dist/` and serves it at <https://localhost:8443>. Any static
  server pointed at `dist/` works too, for example `python3 -m http.server -d dist`.

## Browser support

| Browser | Status |
| --- | --- |
| Chrome, Edge | Full support: hardware H.264 export, linked files, autosave. |
| Safari (recent) | Works; export uses whichever codecs its WebCodecs encoder offers. No linked files. |
| Firefox 130+ | Works, with WebM (VP9) export where H.264 encoding is unavailable. No linked files. |

Linked media relies on the File System Access API, which only Chromium has. Elsewhere, imported
media is always embedded in the project.

## Installing as an app

In Chrome or Edge, open the hosted or local copy and choose **Install** (the icon at the end of
the address bar, or menu → *Cast, save and share* → *Install page as app*). It then opens in its own
window from your app launcher.

## Where your work lives

- **Projects** are `.vproj` files you save and open yourself (Ctrl+S, Ctrl+O, or drop a file on
  the window).
- **Autosave** is kept per site in the browser's private file storage. Clearing site data for the
  page deletes it, and each origin (`localhost:8443`, the Pages URL, a desktop build) has its own.
- **Presets and view settings** are in `localStorage` for the same origin.
