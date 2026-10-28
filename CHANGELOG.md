# Changelog

All notable changes to Overlay Studio, newest first. Work began 2026-10-21.

## [Unreleased]

### Added
- The editor source as `src/index.html`, with docs, a screenshot and the desktop packager in
  `tools/appbundle/`.
- `npm run package:desktop` builds `dist/` and packs it into a desktop app in `dist-desktop/`.

### Changed
- The vendorer rewrites `<script type="importmap">` entries, so three.js and Mediabunny are
  vendored and `dist/` runs fully offline. Prefix mappings (ending in `/`) are left alone.
- Concurrent requests for one URL share a single download.

## Phase 3: safety

### Added
- Autosave to the browser's private file storage (OPFS) a moment after each edit and when the tab
  is hidden or closed. Embedded media is written once per asset, not on every save.
- A recovery dialog on launch when the autosave holds unsaved changes, with Restore and Discard.
- An autosave status chip in the toolbar. Only one tab autosaves at a time.

## Phase 2: motion and keyframes

### Added
- A curve editor under the timeline for per-key custom bezier easing.
- Parenting: any clip can follow another clip, or an avatar's face or body anchor. Changing the
  parent keeps the clip where it is.
- Guides (G): parent links, motion paths for every clip, boxes and handles, with onion skinning.
- Copy and paste style (Ctrl+Alt+C / Ctrl+Alt+V) and named presets under *My presets*.

## Phase 1: layers that filter other layers

### Added
- Adjustment layers: brightness, contrast, saturation, hue, tint, blur, vignette, grain and
  chromatic aberration, applied to everything below or to one clip.
- Effect layers: neon glow, drop shadow, silhouette and contour outlines, shaped by a clip's alpha.
- Title card backgrounds: solid, gradient, image, or a filtered copy of what's below.
- Arrow outline colours, animation styles (draw-on, grow, pulse, bob, marching dashes) and matching
  transitions.

## Round 3: effects, callouts and motion paths

### Added
- Hex vortex backdrop plugin.
- Title clips: title card, lower third, subtitle and plain text.
- Callout shapes (box, rounded box, ellipse, highlighter, bezier arrow) with hand-drawn roughness
  and draw-on animation.
- Redaction clips: blur, pixelate or solid bar, with feathering.
- Sticker options for images (die-cut border, drop shadow) and wiggle on any transformable clip.
- Motion paths with bezier handles.

## Initial editor

### Added
- Single-canvas WebGL compositor shared by preview and export.
- Frame-exact MP4 (H.264) and WebM (VP9) export with WebCodecs and Mediabunny, mixing clip audio
  and audio tracks with waveforms and keyframeable volume.
- Video, image, bubble, avatar and backdrop clips; keyframes with named easings; in/out
  transitions; undo/redo and snapping.
- Speech bubbles that follow an avatar's face or body; auto talking while a linked bubble shows.
- Avatar actions as timeline clips; the ghost ships with nod, shake, jump, spin, boo and shiver.
- Plugin API with parameter schemas, loaded from a URL or a dropped `.js` file. Built-ins: ghost,
  snowfall, star sphere and cloudy sky.
- `.vproj` project files with embedded or linked media, relinking, and save consolidated.
