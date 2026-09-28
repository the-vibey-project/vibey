---
id: skill-4-rendering-c027ccd260
purpose: 4 rendering
source: src/vibey_tools/skills/plugins/video-game-development/skills/game-rendering-physics-animation-and-audio/SKILL.md
requires: []
links: ["skill-5-physics-and-collision-feecf85642"]
---

## §4. Rendering

### 4.1 The pipeline

```
scene → CULLING (frustum, occlusion) → sorting/batching → draw submission
  → vertex/mesh shaders → rasterize → fragment shaders → depth/stencil
    → post-processing (TAA, bloom, tonemap, color grade) → UI → present
```

**Forward** (shade each fragment as drawn — good for MSAA, transparency, mobile, and
tile-based GPUs), **Deferred** (write a G-buffer, then shade — many lights cheaply, but
transparency and MSAA are awkward and bandwidth is high), **Forward+/Clustered** (light
culling into tiles or clusters, then forward-shade — **the mainstream modern answer**),
and **Visibility buffer** (store triangle IDs, shade once per pixel — what Nanite-style
systems do).

### 4.2 Graphics APIs

**[VERSIONED]**

| API | Platforms | Notes |
|---|---|---|
| **Direct3D 12** | Windows, Xbox | DXR ray tracing, VRS, mesh shaders, **DirectStorage**, work graphs. **DX12 Ultimate** is the feature bundle |
| **Vulkan** | Windows, Linux, Android, macOS via MoltenVK | Open, portable, explicit. **Current spec is 1.4**; **Vulkan Roadmap 2026 requires 1.4** and targets mid-to-high-end hardware shipping in 2026 or shortly after, adding baseline requirements like `hostImageCopy` |
| **Metal** | Apple only | The only first-class path on Apple platforms |
| **WebGPU** | Browsers, and increasingly native | The modern web target; also a decent portable abstraction |
| **OpenGL / WebGL** | Legacy | Still relevant for compatibility floors |
| **Console APIs** | NDA'd | GNM/AGC, and the Xbox D3D12 variant |

**[DURABLE] Use your engine's abstraction unless you have a specific reason not to.**
Writing directly against D3D12/Vulkan is a large, ongoing commitment; both are explicit
APIs where *you* manage memory, synchronization, descriptors, and pipeline state.

**[CONTESTED] Whether the explicit APIs are still the right shape.** Sebastian Aaltonen's
widely-discussed argument: DX12, Vulkan, and Metal are now **ten years old and were
designed for GPUs that are thirteen years old**, from an era before bindless resources
were widely supported — with the result that a *new* low-level remapping layer has grown
beneath engines' RHIs, re-assuming the complexity the old drivers used to handle. There is
real disagreement about whether the next step is simpler high-level APIs, further
explicitness, or GPU-driven pipelines making the question moot.

**Modern GPU-driven rendering** is where the field is going: **mesh shaders** (replacing
the vertex/geometry pipeline with amplification+mesh stages over meshlets), **GPU-driven
culling and draw generation**, and **work graphs** (the GPU enqueuing its own work,
shipping in D3D12 and available in Vulkan via `VK_AMDX_shader_enqueue`, **not yet
standardized across vendors**).

> **⚠️ GOTCHA — mesh shaders are not a universal replacement.** Mobile GPUs are
> **tile-based renderers** that bin individual triangles to small tiles; meshlets are too
> coarse-grained for that, and binning them to tiny tiles causes significant geometry
> overshading. **There is no clear convergence path — you still need the vertex-shader
> path.** Any "just switch everything to mesh shaders" plan is a desktop-only plan.

### 4.3 The things that actually cost you

- **Draw calls / CPU submission** — batch, instance, and use indirect draws. Historically
  the #1 CPU bottleneck.
- **Overdraw** — shading pixels that get covered. Depth pre-pass, front-to-back sorting.
- **Bandwidth** — texture reads and G-buffer traffic. **Compress everything** (BC1–BC7 on
  desktop, ASTC on mobile), mip properly, and use the smallest formats that look right.
- **Shader complexity and register pressure** — high register use kills occupancy.
- **State changes and pipeline switches**.
- **⚠️ Shader compilation stutter** — the defining PC technical problem of this
  generation. Compile and cache PSOs **ahead of time**, at load or install; do not compile
  on first use during gameplay. Vulkan's SPIR-V helps by moving parsing offline, but
  driver-side pipeline compilation still happens.

### 4.4 Ray tracing and upscaling

Hardware RT (DXR/Vulkan RT, both organizing geometry into **acceleration structures**) is
now mainstream for reflections, GI, and shadows — usually as an *option* on top of a
raster path, rarely as the only path. **Upscaling (DLSS, FSR, XeSS, MetalFX) and frame
generation** are now assumed in performance budgets rather than treated as a bonus, which
has quietly changed what "runs at 4K60" means. **[DURABLE] Budget for the native
resolution you actually render at, and treat upscaling as a quality lever, not a
substitute for optimization.**

---
