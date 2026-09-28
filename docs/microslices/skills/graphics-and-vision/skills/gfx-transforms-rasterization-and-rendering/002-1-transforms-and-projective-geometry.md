---
id: skill-1-transforms-and-projective-geometry-13dcf23f1f
purpose: 1 transforms and projective geometry
source: src/vibey_tools/skills/plugins/graphics-and-vision/skills/gfx-transforms-rasterization-and-rendering/SKILL.md
requires: ["skill-0-routing-cdc85a380f"]
links: ["skill-2-rasterization-330f988324"]
---

## §1. Transforms and Projective Geometry

**Homogeneous coordinates**: a 3D point becomes `(x, y, z, w)`, with the Euclidean point
recovered as `(x/w, y/w, z/w)`. ⚠️ **`w = 0` denotes a point at infinity — a direction.**
**This is why you must transform normals and positions differently**: positions are
`(x,y,z,1)`, directions `(x,y,z,0)`, so translation applies to one and not the other.

**The pipeline of spaces:**
```
Model → [model matrix] → World → [view matrix] → View/Camera
      → [projection] → Clip → [÷w, perspective divide] → NDC
      → [viewport] → Screen
```
**⚠️ The perspective divide is where the nonlinearity enters** — everything before it is
linear, which is the entire point of homogeneous coordinates.

**⚠️ Normal transformation is the classic bug**: normals transform by the **inverse
transpose** of the model matrix, not the matrix itself. **Under non-uniform scaling, using
the model matrix skews normals off the surface and your lighting is wrong** in a way that
looks like a shading bug rather than a math bug.

**Rotations**: matrices (composable, 9 numbers, drift under repeated multiplication),
**Euler angles** (⚠️ **intuitive and gimbal-locked — avoid for interpolation or
accumulation**), **quaternions** (⚠️ **4 numbers, no gimbal lock, and `slerp` interpolates
correctly — the right internal representation**; note `q` and `−q` are the same rotation,
which trips comparison and naive interpolation), **axis-angle**, and **Lie algebra
(SO(3)/SE(3))** — ⚠️ **the right formulation for optimization, because it gives you a
minimal, unconstrained local parameterization**, which is why SLAM and bundle adjustment
use it (§10 → `gfx-image-formation-classical-vision-and-geometry`).

**⚠️ Conventions that cause days of confusion**: row-vector vs column-vector, row-major vs
column-major storage, left- vs right-handed coordinates, and **NDC depth range —
OpenGL's `[-1,1]` vs D3D/Vulkan/Metal's `[0,1]`.** **Write yours down at the top of the
file.**

---
