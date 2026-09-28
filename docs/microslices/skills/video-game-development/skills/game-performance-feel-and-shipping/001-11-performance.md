---
id: skill-11-performance-bc6ed17f80
purpose: 11 performance
source: src/vibey_tools/skills/plugins/video-game-development/skills/game-performance-feel-and-shipping/SKILL.md
requires: []
links: ["skill-12-game-feel-988ec6f0e7"]
---

## §11. Performance

### 11.1 The budget

```
60 fps → 16.67 ms/frame        120 fps → 8.33 ms
Rough AAA-ish split (illustrative — yours will differ):
  render submission  4–6 ms   |  GPU (parallel)  ~14 ms
  gameplay/scripts   2–4 ms   |  animation       1–3 ms
  physics            1–3 ms   |  AI              1–2 ms
  audio              <1 ms    |  UI              1–2 ms
  streaming/IO       amortized, off the main thread
```
**[DURABLE] Profile before optimizing, on the *lowest-spec target*, and optimize the
frame-time distribution rather than the average.** A game that averages 120 fps with
periodic 40 ms hitches feels worse than a steady 105. **Measure 1% and 0.1% lows.**

### 11.2 Tools
Engine profilers (Unity Profiler, Unreal Insights), **RenderDoc** (frame capture and
debugging — indispensable), **PIX** (Windows/Xbox), **Nsight** and **Radeon GPU
Profiler**, **Tracy** (excellent open-source frame profiler), **Superluminal**, and
platform-specific console profilers under NDA.

### 11.3 CPU

**Cache locality is the whole game** (this is exactly why ECS exists): arrays of structs
of hot data, not pointer-chasing object graphs. **A main-memory miss costs hundreds of
cycles**; you can do a lot of arithmetic in that time.

**Job systems / task graphs** for parallelism — a work-stealing scheduler over a task
graph is the standard architecture, with the caveat that **rendering submission is often
single-threaded-ish and the render thread becomes your bottleneck**.

**Avoid per-frame allocation** entirely (§11.4), avoid virtual calls in the hottest loops,
and **batch by type** so branches predict.

### 11.4 Memory

**[DURABLE] Games are memory-constrained more often than compute-constrained**, especially
on console and mobile, and memory problems present as stutter rather than as low framerate.

- **Object pooling is essential**, not optional. Pre-allocate bullets, particles, enemies,
  UI elements.
- **Custom allocators**: frame/arena allocators (reset every frame — free, and impossible
  to leak), pool allocators, stack allocators.
- **⚠️ GC languages need discipline.** In C# (Unity), every allocation is future GC
  pressure; a GC spike *is* a dropped frame. Avoid LINQ and closures in `Update`, avoid
  boxing, cache arrays, use structs where sensible, and use `NonAlloc` API variants.
- **Streaming and LODs** for large worlds; virtual texturing; **DirectStorage** and
  equivalents for fast asset loading.
- **Fragmentation** matters on consoles with fixed memory and long sessions.

---
