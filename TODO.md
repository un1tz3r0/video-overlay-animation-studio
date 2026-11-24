# TODO

The phased plan from [docs/DESIGN.md](docs/DESIGN.md). Each phase is shipped and tested before the
next starts. Phases 1–3 are done; see [CHANGELOG.md](CHANGELOG.md).

## Phase 4: backdrops from the CodePens

- [ ] **Hex drift.** A depth-layered field of hex outlines drifting sideways and spinning. Depth
  sets size, brightness and paint order, over a gradient with a multiply or colour-dodge blend.
  A port of the cor3llc splash pens.
- [ ] **Sputnik.** A golden-spiral sphere of stems with cone collars and petal or bulb tips that
  slowly tumbles, after the Zdog demo. Built in three.js so it gets lighting and the cartoon outline.

References: [XJdvJzJ](https://codepen.io/un1tz3r0/pen/XJdvJzJ),
[YBmdNL](https://codepen.io/un1tz3r0/pen/YBmdNL), [WNQjbWQ](https://codepen.io/un1tz3r0/pen/WNQjbWQ).

## Phase 5: audio-driven talking

- [ ] **Investigation.** Compare (a) loudness only, (b) a 3–5 band filterbank mapped to mouth open,
  wide and round, and (c) formant tracking mapped to vowel shapes. (b) is expected to give most of
  the realism of (c) at a fraction of the cost.
- [ ] **Build the chosen approach.** Avatar plugins receive `info.mouth = {open, wide, round}`,
  driven by a linked audio clip or by bubble visibility as today.

## Before a public release

- [ ] **Subtitle import and export.** SRT or VTT becomes subtitle clips, and projects export SRT.
- [ ] **Chroma key** on video clips.

## Later

- [ ] **Linked paths.** One path drives others; editing a linked copy or deleting the master asks
  before breaking the link.
- [ ] **Path constraints.** Progress comes from the point on the path nearest another clip or
  anchor, so a clip slides along a rail.

## On hold

- **Point tracking** in video, so a blur box or sticker follows a moving object. Manual keyframes
  and motion paths cover it until in-browser tracking matures.
