> Exported from the living design doc, <https://claude.ai/artifact/3ZQXXQTE9sW8YwhP93cZF2>, on 2026-10-28.
> The phased plan is mirrored in [TODO.md](../TODO.md) and what has shipped in [CHANGELOG.md](../CHANGELOG.md).

# Video overlay editor: design review

Oct 21, 2026 · @Victor Condino

## Summary

I'm building a browser-only, single-file editor on my best reading, and I'll adjust as you answer the questions at the end. Everything visible, including video, stills, 3D layers and speech bubbles, renders into one WebGL canvas through three.js, so preview and export are the same code path. Export uses WebCodecs to encode MP4 (H.264) or WebM (VP9), with a small muxer. Project files are one binary bundle that holds the JSON timeline and the imported media.

Defaults until you say otherwise: 1920×1080 at 30 fps, set per project; tracks stacked bottom to top; keyframes per property with named easings; in and out transitions as presets on each clip; plugins are ES modules that declare a parameter schema the sidebar renders automatically.

## Corrections and better approaches

Five things in the brief would bite us later if we took them literally.

1. **Export should not use MediaRecorder.** It records in real time, drops frames under load, and gives no control over frame timing. ffmpeg.wasm works but is a \~30 MB download and runs 5 to 20 times slower than hardware encoding. WebCodecs `VideoEncoder` is hardware accelerated and frame exact. I'm using [Mediabunny](https://mediabunny.dev) for the muxing; it is pure TypeScript with no dependencies.
2. **`<video>` cannot seek frame-accurately.** Setting `currentTime` lands on whatever frame the browser picks, often the nearest keyframe, and `seeked` timing is unreliable. For export I decode the source with WebCodecs (through Mediabunny's `CanvasSink`), which returns the exact frame for any timestamp. Live preview still uses `<video>`, because it is cheap and smooth.
3. **Speech bubbles must be drawn into the canvas, not the DOM.** DOM elements never reach the encoder. Each bubble is rasterized with Canvas 2D into a texture on a quad in an orthographic overlay. That also lets a bubble follow its speaker, which is optional per bubble. Follow can be: the tail points at the speaker, the whole bubble moves with the speaker at a keyframeable offset, or fixed with a manual tail. Track picks the target: the face bone (follows head pose) or the body (follows only the avatar's position, layer transform and camera, so posing the head or body does not move the bubble). Plugins expose this through anchor('face' | 'body'); a plugin without a body anchor falls back to its scene origin.
4. **Plugins must be pure functions of time.** If a snow plugin integrates `position += velocity * dt`, scrubbing backwards or exporting at a different frame rate gives a different picture. The plugin contract is `update(t, params)` with absolute time, so every frame is reproducible. Snow becomes `y = wrap(y0 - speed * t)`, clouds are noise sampled at `t`, and the ghost's sway is `sin(t)`. This also means "loops" don't need to loop; they just run for the clip's length.
5. **Audio is missing from the brief.** Exporting video without the clip's soundtrack is rarely what anyone wants. I'm carrying source audio through to the export by default, mixed with an `OfflineAudioContext`.

   Separate audio clips (music, voice) now sit on their own tracks with keyframeable volume and fade transitions. They show a waveform on the timeline and mix into the export through the same OfflineAudioContext.

## Architecture

One renderer, one canvas, layers drawn bottom to top with `autoClear` off between them.

- **Compositor.** Video and stills are textured quads in an orthographic scene. Each 3D clip (avatar or background) owns its own `Scene` and camera and is rendered in its track's order. Bubbles render last in a screen-space overlay. Preview and export call the same `renderFrame(t)`.
- **Data model.** A project has `settings` (width, height, fps, duration, background colour), `assets` (id, kind, name, mime, blob), and `tracks`, each holding `clips`. A clip has `type`, `start`, `duration`, `in` (source offset for video), `props`, `keys`, and `transitions`.
- **Keyframes.** `keys[prop] = [{t, v, ease}]`, with `t` relative to the clip start. Numbers, vectors and colours interpolate; strings and booleans step. Each key's `ease` shapes the segment that leaves it. Easings: linear, step, quad/cubic in-out, back, elastic, bounce, and a custom cubic-bezier.
- **Transitions.** `in` and `out` presets (fade, pop, slide from any side, spin, typewriter for text) with their own duration and easing. They apply as modifiers on top of the keyframed values (opacity ×, scale ×, offset +), so they never fight with your keys.
- **Plugin API.** A plugin is an ES module whose default export is `{id, kind: 'avatar' | 'background', name, params, create(ctx)}`. `params` is a schema like `{speed: {type: 'number', min: 0, max: 5, default: 1}}`, which drives the sidebar and makes every parameter keyframeable. `create({THREE, width, height})` returns `{scene, camera?, update(t, p, info), anchor?(kind), dispose?()}`. Avatars expose `anchor()` with 'face' or 'body', the point a bubble follows. An optional actions map declares named actions (see Avatar animation). Plugins load from a URL or a dropped `.js` file through dynamic `import()` of a blob URL.
- **Avatar animation.** Bones are driven by keyframeable params (bend, lean, face yaw and pitch, bob) on top of a procedural idle. A `talking` flag turns on automatically while a bubble linked to that avatar is visible. Plugins can also declare named actions ({label, duration, params}). You drop these on the timeline as action clips: the clip's in and out transitions blend the action in and out, its params are keyframeable, and the plugin receives the active ones in info.actions with local time and weight. An action can do anything the plugin can, including morph targets and per-vertex animation. The ghost ships with nod, shake, jump, spin, boo and shiver.
- **Project file.** A single `.vproj` binary: magic bytes, the JSON length, the JSON, then the raw media blobs with offsets recorded in the JSON. No base64 inflation, and it streams back with `Blob.slice`. Each asset is either embedded (its bytes are in the bundle) or linked (a File System Access handle kept in IndexedDB, so only its metadata goes in the file). A badge in the Media list switches between the two. Missing links show dashed and relink on click, and Save consolidated embeds every linked file. Autosave to OPFS is a cheap follow-up.

## Open questions

Each has the default I'm building with; a one-word answer is enough to change it.

| # | Question | My default |
| --- | --- | --- |
| 1 | Which browsers must it support? WebCodecs encode is solid in Chrome and Edge, newer in Safari and Firefox. | Chromium mainly, codec fallback to VP9/WebM elsewhere |
| 2 | Output size and frame rate: fixed, or per project with presets like 9:16 for Shorts? | Per project, 1080p30 default, presets for 16:9, 9:16, 1:1 |
| 3 | Keep source audio in the export? Any need for added music or voice tracks? | Keep clip audio; separate audio clips would be a nice addition. ducking, compression and agc come later |
| 4 | Can there be several avatars at once, and should each bubble be tied to one avatar with its tail following the face? | Yes to both; tail follows the linked avatar's face bone |
| 5 | How should avatars be animated: keyframed bone controls, named actions from the plugin (wave, nod), or both? | Keyframed controls plus procedural idle and auto talk, both... the actions would be a great shortcut/way for plugins to add complex or annoying to animate by hand actions, as well as mesh based animations that would be impossible to achieve through the regular bone animation system |
| 6 | Bubble styles: speech, thought, shout, caption? Custom fonts? | Speech, thought, shout, caption; system and Google fonts |
| 7 | Does the video need transforms (crop, scale, position) and speed changes, or just trim and place? | Trim, position, scale, opacity; no speed change yet |
| 8 | Should the project file embed media (large but portable) or reference it by name (small, needs relinking)? | Both, with the ability to select external files and make them embedded later on, on the fly, and the ability to consolidate (embed all external) on save. |
| 9 | Where do third-party plugins come from: URL, dropped file, or a folder? Are they trusted? Plugins run with full page access. | URL or dropped file, treated as trusted code |
| 10 | Undo/redo and timeline snapping in the first version? | Yes, both |

## Round 3: effects, callouts and motion paths

This is what I'm building, in this order. The defaults in the questions table below apply until you change them.

1. **Hex vortex backdrop.** Instanced hexagon tiles spiral down a helix around the centre of the frame. Params cover count, radius and spread, fall and swirl speed, twist, tumble, size, look (solid, outline or glass), two tile colours, a background gradient and depth fog. Like the other plugins it is a pure function of time.
2. **Titles.** A new title clip with four styles: full-frame title card, lower third, subtitle (boxed, wrapped, bottom centre) and plain text. It has title and subtitle text, fonts, colours, panel and box settings, and the usual transform. It is rasterized like bubbles, so typewriter and other transitions work.
3. **Callouts.** A new shape clip: box, rounded box, ellipse, highlighter swash and arrow. Settings cover stroke, fill, dash, arrowheads (triangle, open, dot, none, at either end) and a hand-drawn roughness. A keyframeable Draw amount gives the draw-on animation, and there is a Draw transition. An arrow's shape is a bezier path edited with the same handles as motion paths, so straight, curved and S-shaped arrows are all one tool.
4. **Redaction.** A new redact clip: blur, pixelate or a solid bar, as a rectangle or ellipse with feathering. It filters whatever is below it in the stack, like an adjustment layer.
5. **Stickers.** Image clips get a native-size fit, a die-cut border (width, colour) and a drop shadow. A Wiggle group (amount, speed) adds procedural idle motion to any transformable clip.
6. **Motion paths.** Any transformable clip can follow a bezier path you draw in the viewport. Drag points and handles, double-click to add or delete a point, and Alt-drag to pull handles out. A keyframeable Progress % moves the clip along the path by distance, so speed is constant between keys and the keys' easing shapes it. Orient to path rotates the clip along the tangent. Turning a path on seeds it from the clip's current position.
7. Adjustment layers! Layers which filter everything underneath them with some effect with keyframeable parameters.
8. Effects layers, which apply post-processing on the layer immediately below them. This could be used to add effects like neon glow that uses the target layer's transparency to define the shape of the glow to blur and then cut out the interior of, or to add black silhouette and contour outlines to graphics which don't have any outline or shadow of their own.

| # | Question | My default |
| --- | --- | --- |
| 11 | Should a path belong to one clip, or be a shared object several clips can follow? | One path per clip; duplicate the clip to reuse it. For a later pass, extra credit: Possibly add the ability to link one path to another, syncing changes to the master to the linked slave. The link breaks with a warning/confirm prompt if the slave is edited or the master is removed. |
| 12 | Progress by distance (constant speed) or by bezier parameter (speeds up where points are far apart)? | By distance\
\
...or for major extra credit (read: maybe save this for a much later pr): progress by nearest point to some other object or position source, so kindof a constrained object linking, with the linked object limited to points along a path. idk, just an idea. |
| 13 | Redaction: filter everything below it, or only one chosen clip? | Selectable, both should be possible |
| 14 | Title card background: solid, gradient, image, or a flattened filtered copy of what's below? | All four of these should be options |
| 15 | Arrow styles beyond clean and hand-drawn, such as chalk, neon glow or comic outline? | Clean and hand-drawn, plus one or two optional outline colours and widths for contrast. also arrow styles could have their own animation styles and  transition styles. |

### Other ideas, roughly by value for effort

- **Subtitle import:** SRT or VTT becomes subtitle clips, and the project can export SRT too. Small, and useful straight away.
- **Parenting:** any clip can follow another clip or an avatar anchor, generalizing the bubble follow modes. Stickers could ride on an avatar, or a blur box on a moving sticker.
- **Curve editor:** per-key custom easing with draggable bezier handles. This pairs with motion paths for natural motion.
- **Audio-driven talking:** the avatar's mouth follows the loudness of a linked audio clip instead of bubble visibility.
- **Chroma key** on video clips, for green-screen footage.
- **Copy/paste style and presets:** save a clip's look, such as a lower-third style, and reuse it.
- **Autosave** to OPFS, with recovery after a crash.
- **Point tracking** in video, so a blur box or sticker follows a moving object. This is the most useful idea for redaction, and also the most work.

---

Here are a few codepen references for some of the hexagonal and other animated background effects that I have come up with over the years, you can use them for inspo:

- <https://codepen.io/un1tz3r0/pen/XJdvJzJ>
- <https://codepen.io/un1tz3r0/pen/YBmdNL>
- <https://codepen.io/un1tz3r0/pen/WNQjbWQ>

## TODO: phased plan

Five phases, each shipped and tested before the next starts. Phase 1 settles your answers to #13–15 and adds the two new layer kinds, because they share one rendering change.

### Phase 1: layers that filter other layers

- [x] **Shared plumbing.** Every filtering layer gets a Target setting: *Everything below* (the composite so far) or *One clip* (a picker, which renders only that clip offscreen). This answers #13 for redaction and powers the two items below.
- [x] **Adjustment layers.** A new clip type that filters everything below it, with keyframeable brightness, contrast, saturation, hue, tint, blur, vignette, grain and chromatic aberration. Redaction stays as its own clip and reuses the same code.
- [x] **Effect layers.** A new clip type that post-processes one clip, by default the clip directly below it in the stack. The effect is shaped by that clip's alpha. Effects: neon glow (blurred alpha, interior optionally cut out), drop shadow, solid silhouette, and contour outlines (one or more rings at set widths). Several effect layers can stack.
- [x] **Title card backgrounds (#14).** Solid, gradient, image (any image asset, fit cover or contain), or a flattened, filtered copy of what's below, using the adjustment filters.
- [x] **Arrow styles (#15).** One or two outline colours, each with its own width. Arrows also get animation styles that run while the clip is up (draw-on, grow from tail, pulse, bob, marching dashes) and matching in and out transitions.

### Phase 2: motion and keyframes

- [x] **Curve editor.** Per-key custom easing with draggable bezier handles, in a panel under the timeline.
- [x] **Parenting.** Any clip can follow another clip or an avatar anchor, which generalizes the bubble follow modes.
- [x] **Editor overlay.** One View toggle shows or hides lines for parent links, motion paths for every clip (not just the selected one), boxes and handles. An onion-skin option ghosts those annotations at nearby keys.
- [x] **Copy/paste style and presets.** Copy a clip's look onto another clip of the same type, and save named presets to the Overlays panel.

### Phase 3: safety

- [x] **Autosave and crash recovery.** The project is saved to the browser's private file storage every few seconds and after each edit. On the next launch, if the last session did not close cleanly, the editor offers to restore that save. Embedded media is stored once, not on every save.

### Phase 4: backdrops from your CodePens

- [ ] **Hex drift.** A depth-layered field of hex outlines drifting sideways and spinning. Depth sets size, brightness and paint order, over a gradient with a multiply or colour-dodge blend. This is a port of the cor3llc splash pens.
- [ ] **Sputnik.** A golden-spiral sphere of stems with cone collars and petal or bulb tips that slowly tumbles, after the Zdog demo. It is built in three.js so it gets lighting and the cartoon outline.

### Phase 5: audio-driven talking

- [ ] **Investigation first.** I'll write up a short comparison here before building: (a) loudness only, (b) a 3–5 band filterbank mapped to mouth open, wide and round, and (c) formant tracking (estimating the two strongest vocal resonances each frame) mapped to vowel shapes. I expect (b) to give most of the realism of (c) at a fraction of the cost.
- [ ] **Build the chosen approach.** Avatar plugins receive `info.mouth = {open, wide, round}`, driven by a linked audio clip or by bubble visibility as today.

### Backlog: before a public release

- [ ] **Subtitle import and export.** SRT or VTT becomes subtitle clips, and the project can export SRT.
- [ ] **Chroma key** on video clips, for green-screen footage.

### Later, extra credit

- [ ] **Linked paths (#11).** One path drives others. Editing a linked copy or deleting the master asks before breaking the link.
- [ ] **Path constraints (#12).** Progress comes from the point on the path nearest another clip or anchor, so a clip slides along a rail.

### On hold, no ETA

- **Point tracking.** It would save the most time for redaction and stickers, but it is a large, unsettled piece of work. It needs per-frame feature tracking in the browser. Optical flow on the GPU drifts and loses occluded points. Learned trackers are robust but need large models on WebGPU, which is still uneven across browsers, and they are slow on long clips. Manual keyframes plus motion paths cover it until the tooling matures.

## Implementation notes

Where the shipped editor differs from the text above:

- **Presets** live in the Assets panel under *My presets*, and in the Add menu, rather than in a separate Overlays panel.
- **Paste style** works across clip types: it copies the properties the two types share and skips the rest.
- **Recovery** is offered whenever the autosave holds unsaved changes, not only after a crash. Closing the tab with unsaved edits counts too.
- **Plugin cameras** are required: `create()` must return a `camera` along with the `scene`.
