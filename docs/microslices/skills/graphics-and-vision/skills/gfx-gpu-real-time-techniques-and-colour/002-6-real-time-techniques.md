---
id: skill-6-real-time-techniques-597f5adbcd
purpose: 6 real time techniques
source: src/vibey_tools/skills/plugins/graphics-and-vision/skills/gfx-gpu-real-time-techniques-and-colour/SKILL.md
requires: ["skill-5-gpu-architecture-and-apis-1a0f2e48ff"]
links: ["skill-7-colour-and-tone-mapping-1a2f4c24e8"]
---

## §6. Real-Time Techniques

**Shadows**: **shadow mapping** — render depth from the light, compare. ⚠️ **Shadow acne
(self-shadowing from depth precision) and peter-panning (from over-biasing) are the two
failure modes, and normal-offset bias handles both better than constant bias.**
**Cascaded shadow maps** for directional lights, **PCF/PCSS** for soft edges,
**variance/moment** shadow maps.

**Antialiasing**: **MSAA** (⚠️ **supersamples coverage and depth but shades once — cheap
and effective for geometric edges, useless for shader aliasing**), **FXAA/SMAA**
(post-process), **TAA** — ⚠️ **jitter the projection per frame and accumulate with
reprojection. It's the modern default and it brings ghosting, blur and disocclusion
artifacts that require history rejection heuristics to manage.**
**Upscaling**: DLSS, FSR, XeSS, TSR — ⚠️ **temporal upscalers are TAA generalized, and
they are now the assumed rendering path rather than an optional extra.**

**Deferred vs forward**: **deferred** decouples geometry from lighting via a G-buffer —
⚠️ **many lights become cheap, but transparency and MSAA become hard.** **Forward+ /
clustered** — light culling into tiles or clusters, keeping forward's flexibility.
**Visibility buffer** for very high geometry density.

**Global illumination, approximated**: lightmaps (static, still the highest quality per
frame), irradiance probes, **SSAO/GTAO**, **SSR** (⚠️ **screen-space reflections cannot
reflect what's off-screen or behind geometry — the artifact is inherent, not a bug**),
voxel GI, and **hardware-RT GI**.

**⚠️ The through-line for all of §6**: every technique here is a way of estimating §4 → `gfx-transforms-rasterization-and-rendering`'s
integral within about 16 or 8 milliseconds. **Knowing what each one approximates tells you
what its artifacts will be.**

---
