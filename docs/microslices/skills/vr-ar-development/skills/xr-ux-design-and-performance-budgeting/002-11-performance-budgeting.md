---
id: skill-11-performance-budgeting-02f5cdf40e
purpose: 11 performance budgeting
source: src/vibey_tools/skills/plugins/vr-ar-development/skills/xr-ux-design-and-performance-budgeting/SKILL.md
requires: ["skill-10-ux-design-for-3d-fa04a29e0e"]
links: []
---

## §11. Performance Budgeting

**⚠️ The budget is brutal and it is per-eye.** At **90 Hz you have 11.1 ms for two eyes**;
at 120 Hz, **8.3 ms.** ⚠️ **And on standalone hardware you're on a mobile SoC with a
thermal ceiling — sustained performance is well below burst performance, so profile after
20 minutes, not after 20 seconds.**

**Where the time goes**: draw calls and CPU submission (⚠️ **batch aggressively; single-pass
stereo, §4.1 → `xr-rendering-input-and-spatial-understanding`**), overdraw and fill rate (⚠️ **the usual mobile-XR killer**), bandwidth
(TBDR, §4.4 → `xr-rendering-input-and-spatial-understanding`), shader complexity, and physics.

**Levers**: aggressive LOD, occlusion culling, **baked lighting** (⚠️ **lightmaps remain
the best quality-per-millisecond in XR**), **FFR** (§4.3 → `xr-rendering-input-and-spatial-understanding`), texture atlasing, **GPU
instancing**, simplified shaders, and **reducing render scale before reducing frame rate**
— ⚠️ **frame rate is non-negotiable in a way resolution isn't.**

**⚠️ Profile on device.** The editor and a desktop GPU tell you almost nothing about a
standalone headset. **RenderDoc, the platform's own profilers, and frame-time histograms
rather than averages** — ⚠️ **because a 1% frame spike is a visible, presence-breaking
hitch and averages hide it completely.**
