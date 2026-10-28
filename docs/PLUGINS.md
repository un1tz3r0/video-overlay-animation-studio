# Writing plugins

Avatars and backdrops are plugins: ES modules whose default export describes the layer. Load one
with the **Plugin** button in the Assets panel (from a URL or a file), or drop a `.js` / `.mjs` file
on the window. Loaded plugins
are saved inside the project, so a `.vproj` opens with the plugins it uses.

Plugins run as page code with full access to it, so only load ones you trust.

## The contract

```js
export default {
  id: 'my-plugin',              // unique; a second plugin with the same id replaces the first
  kind: 'background',           // 'background' or 'avatar'
  name: 'My plugin',            // shown in the Add menu
  params: { /* name: schema */ },
  actions: { /* avatars only, optional */ },
  create({ THREE, width, height, rng, fullscreen }) {
    return { scene, camera, update(t, params, info) {}, anchor(kind) {}, dispose() {} };
  },
};
```

`create` runs once per clip and receives:

| Key | |
| --- | --- |
| `THREE` | The editor's three.js module. Use it rather than importing your own copy. |
| `width`, `height` | Project size in pixels. |
| `rng(seed)` | A seeded generator returning floats in [0, 1), for stable randomness. |
| `fullscreen(uniforms, fragmentShader)` | A screen-filling quad drawn behind everything, with `vUv` in the shader. |

It returns:

| Key | |
| --- | --- |
| `scene`, `camera` | Required. The layer renders `scene` through `camera` into the clip's box. |
| `update(t, params, info)` | Called every frame before rendering. |
| `anchor(kind)` | Avatars: a world-space `THREE.Vector3` for `'face'` or `'body'`. Bubbles and parented clips follow it. Without it, the face has no anchor and the body is the scene origin. |
| `dispose()` | Free geometry, materials and textures. |

### Time

`update` gets the clip's local time `t` in seconds. It must be a **pure function of `t` and
`params`**: the same inputs give the same picture. Scrubbing jumps around and export renders frames
at the project's frame rate, so anything integrated frame to frame (`pos += vel * dt`) drifts.
Compute state from `t` directly, for example `y = wrap(y0 - speed * t)`.

### Parameters

Each entry in `params` becomes a sidebar control, and number and colour params can be keyframed.

| `type` | Fields | Value |
| --- | --- | --- |
| `number` | `label, default, min, max, step` | number |
| `color` | `label, default` | `'#rrggbb'` |
| `select` | `label, default, options` (array of strings) | string |
| `bool` | `label, default` | boolean |
| `textarea` | `label, default` | string |

Add `group: 'Name'` to put a control in a collapsible group, and `anim: false` to hide its keyframe
button, as for a count that sizes geometry.

### Info

| Key | |
| --- | --- |
| `talking` | 0–1. Rises while a bubble linked to this avatar is visible, following its transitions. |
| `actions` | Active action clips on this avatar: `{name, t, u, duration, weight, params}`, where `u` is `t / duration` and `weight` follows the clip's in and out transitions. |
| `width`, `height` | Project size. |

### Actions

Avatars can declare named actions, which users drop on the timeline as action clips:

```js
actions: {
  hop: { label: 'Hop', duration: 1, params: { height: { type: 'number', label: 'Height', default: 1, min: 0, max: 3, step: .01 } } },
},
```

The plugin applies them in `update` from `info.actions`, scaled by each entry's `weight`.

## Example

A complete backdrop: a field of rotating rings over a vertical gradient. Save it as `rings.js` and
drop it on the editor.

```js
export default {
  id: 'rings', kind: 'background', name: 'Rings',
  params: {
    top: { type: 'color', label: 'Top', default: '#101526' },
    bottom: { type: 'color', label: 'Bottom', default: '#3a4a78' },
    ring: { type: 'color', label: 'Rings', default: '#e8ecff' },
    count: { type: 'number', label: 'Count', default: 40, min: 1, max: 200, step: 1, anim: false },
    speed: { type: 'number', label: 'Spin speed', default: .5, min: -3, max: 3, step: .01 },
    drift: { type: 'number', label: 'Drift', default: .3, min: 0, max: 2, step: .01 },
  },
  create({ THREE, width, height, rng, fullscreen }) {
    const scene = new THREE.Scene(), camera = new THREE.PerspectiveCamera(50, width / height, .1, 100);
    camera.position.z = 10;
    const sky = { top: { value: new THREE.Color() }, bottom: { value: new THREE.Color() } };
    scene.add(fullscreen(sky, `uniform vec3 top, bottom; varying vec2 vUv;
      void main() { gl_FragColor = vec4(mix(bottom, top, vUv.y), 1.); }`));
    const geo = new THREE.TorusGeometry(.5, .04, 8, 48), mat = new THREE.MeshBasicMaterial();
    const r = rng(3), rings = Array.from({ length: 200 }, () => {
      const m = new THREE.Mesh(geo, mat);
      m.userData = { x: r() * 16 - 8, y: r() * 10 - 5, z: -r() * 8, phase: r() * Math.PI * 2, s: .5 + r() };
      m.scale.setScalar(m.userData.s);
      scene.add(m);
      return m;
    });
    return {
      scene, camera,
      update(t, p) {
        sky.top.value.set(p.top); sky.bottom.value.set(p.bottom); mat.color.set(p.ring);
        rings.forEach((m, i) => {
          const { x, y, z, phase } = m.userData;
          m.visible = i < p.count;
          m.position.set(x, y + Math.sin(t * p.drift + phase) * .5, z);
          m.rotation.set(t * p.speed + phase, t * p.speed * .7, 0);
        });
      },
      dispose() { geo.dispose(); mat.dispose(); },
    };
  },
};
```

The built-in plugins near the `/* ---------- built-in plugins ---------- */` marker in
`src/index.html` are longer examples: the ghost avatar shows bones, anchors, talking and actions.

## Scripting the editor

`window.overlayStudio` exposes the editor to the console and to plugins: `THREE`, `store`,
`engine`, `registerPlugin(def)`, `addClip`, `importFiles`, `saveProject`, `openProject`,
`exportVideo`, `evalAll`, `presets`, `copyStyle`, `pasteStyle` and `autosave`.
`overlayStudio.registerPlugin(def)` registers a plugin object directly, without a file.

## Project file format

A `.vproj` file is little-endian binary:

| Offset | Size | |
| --- | --- | --- |
| 0 | 4 | `VPRJ` |
| 4 | 4 | Format version, `1` |
| 8 | 4 | JSON length *n* in bytes |
| 12 | *n* | UTF-8 JSON: `{version, project, plugins}` |
| 12 + *n* | | Embedded media, back to back |

`project.assets[]` entries for embedded media carry `offset` (from the end of the JSON) and `size`.
Linked assets have neither and are relinked from the browser's saved file handles. `plugins` holds
the source text of every loaded plugin.
