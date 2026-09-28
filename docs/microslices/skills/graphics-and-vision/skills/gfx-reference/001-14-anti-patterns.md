---
id: skill-14-anti-patterns-589685f54e
purpose: 14 anti patterns
source: src/vibey_tools/skills/plugins/graphics-and-vision/skills/gfx-reference/SKILL.md
requires: []
links: ["skill-15-numbers-ed3426537d"]
---

## §14. Anti-Patterns

| Anti-pattern | Why |
|---|---|
| Transforming normals by the model matrix | ⚠️ **Use the inverse transpose** (§1 → `gfx-transforms-rasterization-and-rendering`) |
| Euler angles for interpolation or accumulation | Gimbal lock, drift (§1 → `gfx-transforms-rasterization-and-rendering`) |
| Lighting or blending in sRGB space | ⚠️ **The most common correctness bug in graphics** (§7 → `gfx-gpu-real-time-techniques-and-colour`) |
| Screen-space linear interpolation of attributes | ⚠️ **Must be perspective-correct** (§2 → `gfx-transforms-rasterization-and-rendering`) |
| Near plane at 0.001 to "be safe" | ⚠️ **Destroys depth precision. Z-fighting follows** (§2 → `gfx-transforms-rasterization-and-rendering`) |
| Fragment shader writing depth or using `discard` unnecessarily | ⚠️ **Kills early-Z silently** (§2 → `gfx-transforms-rasterization-and-rendering`) |
| Disabling mipmaps for sharpness | ⚠️ **They're antialiasing, not an optimization** (§2 → `gfx-transforms-rasterization-and-rendering`) |
| Intermediate metallic values | Physically meaningless (§3 → `gfx-transforms-rasterization-and-rendering`) |
| Constant shadow bias | ⚠️ **Acne or peter-panning. Use normal-offset** (§6 → `gfx-gpu-real-time-techniques-and-colour`) |
| Expecting SSR to reflect off-screen geometry | ⚠️ **Inherent limitation, not a bug** (§6 → `gfx-gpu-real-time-techniques-and-colour`) |
| Assuming hardware RT makes path tracing free | It accelerates queries; sampling still dominates (§4 → `gfx-transforms-rasterization-and-rendering`) |
| Branching on non-uniform values in a hot shader | ⚠️ **Warp divergence executes both paths** (§5 → `gfx-gpu-real-time-techniques-and-colour`) |
| Ignoring Vulkan/D3D12 validation layers | ⚠️ **Barrier races appear on one vendor only** (§5 → `gfx-gpu-real-time-techniques-and-colour`) |
| Calibrating with a board that never tilts | ⚠️ **Focal length and distance stay unseparable** (§8 → `gfx-image-formation-classical-vision-and-geometry`) |
| Calibration target that misses the image corners | Distortion goes unconstrained (§8 → `gfx-image-formation-classical-vision-and-geometry`) |
| Polynomial radial distortion on a fisheye | ⚠️ **Wrong model entirely** (§8 → `gfx-image-formation-classical-vision-and-geometry`) |
| Unnormalized 8-point algorithm | ⚠️ **Numerically terrible. Hartley-normalize** (§10 → `gfx-image-formation-classical-vision-and-geometry`) |
| Expecting absolute scale from a monocular sequence | ⚠️ **Inherent ambiguity** (§10 → `gfx-image-formation-classical-vision-and-geometry`) |
| Feature matching without RANSAC | Outliers are guaranteed (§9 → `gfx-image-formation-classical-vision-and-geometry`) |
| Stereo depth quoted without stating range | ⚠️ **Error grows with distance squared** (§10 → `gfx-image-formation-classical-vision-and-geometry`) |
| Augmentation that breaks task invariance | ⚠️ **Silently caps your ceiling** (§11 → `gfx-deep-learning-neural-rendering-and-performance`) |
| Reporting test-set accuracy as deployment performance | ⚠️ **Domain shift is where vision fails** (§11 → `gfx-deep-learning-neural-rendering-and-performance`) |
| Optimizing the model before profiling the pipeline | ⚠️ **Decode and resize are often the bottleneck** (§13 → `gfx-deep-learning-neural-rendering-and-performance`) |
| Expecting clean meshes or relighting from 3DGS | Both are open problems (§12 → `gfx-deep-learning-neural-rendering-and-performance`) |

---
