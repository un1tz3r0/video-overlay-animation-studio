# Desktop app

`tools/appbundle` packs the offline build into one executable. Launching it serves the files on
`127.0.0.1` and opens them in a Chromium app window (Chrome, Edge or Brave, falling back to the
default browser). It exits when the window closes. Details are in
[tools/appbundle/README.md](../tools/appbundle/README.md).

## Requirements

- Node 18+ for the build
- Python 3.10+ with `pip install aiohttp yarl pyinstaller`
- A Chromium browser on the machine that runs the app, for the app window

## Build

```sh
npm run package:desktop
```

That runs `npm run build`, then

```sh
python3 tools/appbundle/appbundle.py build dist/index.html dist/vendor \
  -n "Overlay Studio" --windowed -o dist-desktop
```

and leaves the app in `dist-desktop/`, named from the app name: `overlay-studio` on Linux,
`overlay-studio.exe` on Windows and an `.app` bundle on macOS. The Linux binary is about 33 MB. On Windows, where the interpreter is usually `python`, run the
second command by hand.

To try it without packaging:

```sh
python3 tools/appbundle/appbundle.py run dist/index.html dist/vendor -n "Overlay Studio"
```

## Notes

- PyInstaller builds only for the OS it runs on. The appbundle README has a GitHub Actions matrix
  for all three.
- The binaries are unsigned. macOS Gatekeeper and Windows SmartScreen ask for confirmation on first
  launch.
- The port is derived from the app name, so autosave and presets survive restarts. Renaming the app
  starts with empty storage.
