---
id: skill-4-ray-tracing-and-the-rendering-equation-0089667957
purpose: 4 ray tracing and the rendering equation
source: src/vibey_tools/skills/plugins/graphics-and-vision/skills/gfx-transforms-rasterization-and-rendering/SKILL.md
requires: ["skill-3-shading-and-pbr-9a061209f6"]
links: []
---

## §4. Ray Tracing and the Rendering Equation

**Kajiya, 1986** — ⚠️ **the ground truth for all of rendering:**
```
L_o(x, ω_o) = L_e(x, ω_o) + ∫_Ω f_r(x, ω_i, ω_o) · L_i(x, ω_i) · (n·ω_i) dω_i
```
**Outgoing radiance = emitted + integral over the hemisphere of incoming radiance times
BRDF times cosine.** ⚠️ **It's recursive — `L_i` is some other surface's `L_o` — which is
why global illumination is expensive and why every real-time technique is an
approximation of this integral.**

**Monte Carlo estimation**: sample directions, weight by `1/pdf`. **Variance falls as
`1/√N`** — ⚠️ **so halving noise costs 4× the samples, which is the fundamental economics
of path tracing.**
**Variance reduction**: **importance sampling** (⚠️ **sample proportional to the
integrand — the single biggest win**), multiple importance sampling (**MIS** — Veach),
next-event estimation, Russian roulette for unbiased termination, and stratification /
low-discrepancy sequences.

**Acceleration structures**: **BVH** (⚠️ **the standard; built with SAH — the surface area
heuristic**), kd-tree, grids. **Ray-triangle intersection**: Möller-Trumbore.

**⚠️ Denoising is now part of the algorithm, not a post-process** — real-time ray tracing
traces roughly one sample per pixel and relies on spatiotemporal denoising (SVGF, and ML
denoisers like OptiX/OIDN) to be viable at all.

**Hardware ray tracing** (RTX/DXR/Vulkan RT) accelerates BVH traversal and intersection.
⚠️ **It does not make path tracing free — it makes ray *queries* fast, and the sampling
and denoising budget still dominates.**
