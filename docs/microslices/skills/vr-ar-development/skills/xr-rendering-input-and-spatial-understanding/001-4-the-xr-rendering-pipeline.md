---
id: skill-4-the-xr-rendering-pipeline-ca2256c541
purpose: 4 the xr rendering pipeline
source: src/vibey_tools/skills/plugins/vr-ar-development/skills/xr-rendering-input-and-spatial-understanding/SKILL.md
requires: []
links: ["skill-5-input-and-interaction-17085c4c8b"]
---

## §4. The XR Rendering Pipeline

### 4.1 Stereo
**Two views with an eye offset (the IPD), each with its own asymmetric projection matrix**
— ⚠️ **the frustums are off-axis, not simply translated, and getting that wrong produces
subtle depth discomfort that's hard to diagnose.**

**⚠️ Do not naively render everything twice.** The optimizations:
- **Single-pass / multiview** — ⚠️ **one geometry pass, two render targets via a
  geometry-shader-free instancing path. The standard win, roughly halving CPU draw
  overhead.**
- **Instanced stereo**, **view-dependent culling**, and ⚠️ **stereo-aware shadow and
  reflection passes that are shared rather than duplicated.**

### 4.2 Reprojection — the safety net
**⚠️ This is the mechanism that makes XR tolerable and it deserves to be understood.**
- **Timewarp / ATW (asynchronous timewarp)**: ⚠️ **just before scanout, re-warp the
  rendered frame using the very latest head orientation.** **Corrects rotational error
  only, cheaply** — and it's what decouples perceived latency from frame time.
- **Spacewarp / ASW**: ⚠️ **synthesizes an intermediate frame from motion vectors when you
  miss frame rate.** **Extrapolation, so it produces artifacts around fast-moving objects
  and disocclusions.**
- **Positional timewarp** corrects translation too, and needs depth.

> **⚠️ GOTCHA — reprojection is a safety net, not a performance budget.** It is designed
> for the occasional missed frame. ⚠️ **Shipping a title that relies on ASW to hit its
> target frame rate produces a permanently artifacted experience**, and on some platforms
> it will fail certification. **Hit native frame rate; let reprojection catch the
> outliers.**

### 4.3 Foveated rendering
**Render at full resolution where the user is looking and lower resolution in the
periphery** — ⚠️ **justified because human acuity falls sharply with eccentricity.**
- **Fixed foveated rendering (FFR)** — ⚠️ **no eye tracking needed; exploits the fact that
  lens distortion already wastes samples at the edges. Free performance, widely used.**
- **Eye-tracked foveated rendering (ETFR)** — ⚠️ **much larger savings, and it needs the
  gaze latency budget from §1.1 → `xr-perceptual-constraints-displays-and-tracking` (42–91 ms tolerable, far looser than head MTP).**

### 4.4 The rest of the XR-specific budget
**⚠️ MSAA is preferred over TAA in XR** — TAA's ghosting and blur are far more objectionable
in a stereo, head-tracked display than on a monitor, and ⚠️ **temporal artifacts break
presence.**
**Forward rendering is often preferred** over deferred, because MSAA works with it and
bandwidth is precious on mobile chips.
**⚠️ Mobile XR is tile-based deferred rendering (TBDR)** — which means **avoid
mid-frame render target switches, avoid reading back, and keep the tile resident.**
**Resolution**: render target is typically **1.2–1.4× display resolution** to survive
distortion resampling (§2 → `xr-perceptual-constraints-displays-and-tracking`).

---
