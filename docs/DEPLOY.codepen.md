# Publishing to CodePen

CodePen loads the CDN imports itself, so a pen uses the original `src/index.html`, not the
vendored build.

## New pen

```sh
npm run codepen
```

This writes `dist-codepen.html`, a form that posts the source to CodePen's prefill endpoint. Open it
in a browser and press **Create CodePen**. The whole file lands in the HTML panel; the inline
`<script>` and `<style>` blocks run as they are, so there is nothing to split into the JS and CSS
panels.

## Updating a pen

Open the pen and paste in the new `src/index.html`, or connect the pen to this repository with
CodePen's GitHub integration and sync `src/`.

## Limits in a pen

The pen runs inside an iframe on `cdpn.io`. The File System Access save picker is blocked there,
so saving falls back to a download, and linked media is unavailable. Autosave and export work.
