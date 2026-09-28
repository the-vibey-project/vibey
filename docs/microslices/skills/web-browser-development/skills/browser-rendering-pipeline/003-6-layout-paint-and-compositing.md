---
id: skill-6-layout-paint-and-compositing-762ef5074f
purpose: 6 layout paint and compositing
source: src/vibey_tools/skills/plugins/web-browser-development/skills/browser-rendering-pipeline/SKILL.md
requires: ["skill-5-css-and-style-dd8f2a97f1"]
links: ["skill-7-javascript-integration-aca3e44e21"]
---

## §6. Layout, Paint, and Compositing

### 6.1 The rendering pipeline

**[ENGINE — Chromium's RenderingNG names the stages; every engine has equivalents]:**
```
ANIMATE    mutate computed styles and property trees over time
STYLE      apply CSS to the DOM → computed styles
LAYOUT     compute size and position → the IMMUTABLE FRAGMENT TREE
PRE-PAINT  compute property trees; invalidate display lists and texture tiles
SCROLL     update scroll offsets by mutating property trees
PAINT      compute a DISPLAY LIST describing how to raster
COMMIT     copy property trees and display lists to the compositor
LAYERIZE   group display items into composited layers  (CompositeAfterPaint)
RASTER     display list → GPU texture tiles
ACTIVATE / AGGREGATE / DRAW   assemble and execute the compositor frame on the GPU
```

**[DURABLE] The crucial property: stages can be skipped.** Animating `transform` or
`opacity`, and scrolling, mutate only property trees — so they skip style, layout,
pre-paint, and paint entirely and **run on the compositor thread**, never touching the main
thread. That is exactly why "animate transform/opacity, not width/height/top/left" is the
universal performance advice, and why an engine's threading architecture is a *developer-
facing* fact.

### 6.2 The key data structures

- **Fragment tree** — LayoutNG's output. **Immutable.** The predecessor was a single
  long-lived mutable tree where each node held both inputs (available size, float
  positions) and outputs (final geometry), dirtied and re-cleaned in place. Making layout
  results immutable is what made caching and incremental layout predictable — this is the
  single most instructive architectural lesson in modern rendering.
- **Property trees** — separate transform, clip, effect, and scroll hierarchies. They
  collapse the combinatorial complexity of nested effects into one structure usable at
  every pipeline stage, and they're what lets the compositor animate without the main
  thread.
- **Display lists and paint chunks** — the input to raster and layerization.
- **Compositor frames** — surfaces, render surfaces, and GPU texture tiles.
- **Frame trees** — local and remote nodes recording which document is in which renderer
  process (this is where Site Isolation meets rendering: a cross-site iframe is a *remote*
  frame, rendered elsewhere and composited in).

### 6.3 Layout algorithms

You must implement, correctly and interoperably: **block and inline** formatting contexts
(including floats, margin collapsing, and line breaking — the oldest and gnarliest code in
any engine), **flexbox**, **grid** (and **subgrid**), **tables** (an algorithm nobody
enjoys and everybody needs), **positioned layout**, **fragmentation** (multicol, print,
and page breaking), **writing modes** (vertical text, RTL — and these interact with
everything), and **text shaping** (HarfBuzz-class complexity: ligatures, bidi per UAX #9,
grapheme clusters, font fallback).

> **⚠️ GOTCHA — text is harder than layout.** Font fallback, shaping, bidi, line-breaking
> per UAX #14, and emoji sequences are collectively a larger correctness surface than the
> box algorithms, and getting them wrong is immediately visible to users in languages the
> implementers don't read.

### 6.4 The compositor and the GPU

**[DURABLE] Two threads, and the split is the whole design.** The **main thread** runs
JS, style, layout, and paint. The **compositor thread** handles scroll, composited
animations, and frame submission. If the main thread is blocked for 500 ms, scrolling
still works — that is the entire justification for the architecture's complexity.

- **Layerization** — deciding what gets its own texture. Too few layers means repainting on
  every animation frame; too many exhausts GPU memory. `will-change` is the author-facing
  hint, and it is routinely abused into the second failure mode.
- **Raster** — display list → texture tiles, on worker threads or the GPU (Skia; Chromium's
  newer path via Dawn/**WebGPU**-adjacent infrastructure). Tiling exists so you only raster
  what's near the viewport.
- **Frame budget**: **16.6 ms at 60 Hz, 8.3 ms at 120 Hz** — and that's the budget for
  *everything*, including the compositor's own work.
- **Checkerboarding** — when the compositor needs content that isn't rastered yet, it
  shows old content or a blank pattern rather than dropping the frame. Preferring a stale
  frame to a late frame is the correct trade and worth internalizing.
- **GPU process isolation** — GPU drivers are large, buggy, vendor-supplied C code.
  Running them in a separate sandboxed process is standard, and **Chromium is deploying
  MiracleObject on the GPU main thread specifically targeting up to ~90% of UAF
  vulnerabilities there**, deliberately trading localized runtime performance for temporal
  memory safety.

---
