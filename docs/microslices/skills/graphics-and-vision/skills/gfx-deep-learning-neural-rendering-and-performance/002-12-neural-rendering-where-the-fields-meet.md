---
id: skill-12-neural-rendering-where-the-fields-meet-ce54d7908d
purpose: 12 neural rendering where the fields meet
source: src/vibey_tools/skills/plugins/graphics-and-vision/skills/gfx-deep-learning-neural-rendering-and-performance/SKILL.md
requires: ["skill-11-deep-learning-for-vision-4ba4602bbd"]
links: ["skill-13-performance-cc5061d73d"]
---

## §12. Neural Rendering — Where the Fields Meet

**⚠️ The problem: novel view synthesis.** Given photos of a scene, render it from a
viewpoint you never captured. **This is vision (recover the scene) and graphics (render
it) as a single optimization**, and it's the most significant development in either field
in a decade.

**NeRF (2020)** — represent the scene as a continuous function `(x, y, z, θ, φ) →
(colour, density)`, learned as an MLP, rendered by **volumetric ray marching**, optimized
by comparing rendered pixels to captured photos. **Differentiable rendering is the key
idea** — the renderer is the loss function's forward pass.
⚠️ **NeRF's problem was always cost**: volumetric rendering requires many network
evaluations per ray. Instant-NGP's multiresolution hash encoding cut training to minutes;
rendering stayed slow.

**3D Gaussian Splatting (Kerbl et al., SIGGRAPH 2023)** — represent the scene as millions
of **anisotropic 3D Gaussian ellipsoids** with position, covariance, opacity, and
view-dependent colour via spherical harmonics. **Initialize from SfM points, then
interleave optimization with adaptive density control (splitting and cloning Gaussians
where reconstruction error is high), and rasterize with a fast visibility-aware
differentiable splatting algorithm.**

> **⚠️ The conceptual point that makes 3DGS click**: it is **explicit, not neural.**
> ⚠️ **There is no network evaluated at render time at all** — it's a rasterization of
> primitives, which is why it hits real-time on a GPU that was already built to rasterize.
> **The "neural" part is the optimization, not the representation.** ⚠️ **It's also not
> new in lineage — EWA splatting dates to 2002; what changed is differentiable
> optimization and adaptive densification.**

**§16.1 → `gfx-reference` for the current state.**

**⚠️ Limitations worth knowing regardless of version**: specular and reflective surfaces
are handled poorly (spherical harmonics can't represent view-dependent reflection well,
and the optimizer compensates by scattering Gaussians, hurting geometry); extracting a
clean **mesh** from either representation is a separate, imperfect step; **relighting** is
mostly unsolved because appearance and illumination are entangled; and **memory/storage**
for high-fidelity scenes is large, which is why compression is such an active area.

---
