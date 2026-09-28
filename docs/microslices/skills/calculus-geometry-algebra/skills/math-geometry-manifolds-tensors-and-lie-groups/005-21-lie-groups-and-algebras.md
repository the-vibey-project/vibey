---
id: skill-21-lie-groups-and-algebras-c151760c46
purpose: 21 lie groups and algebras
source: src/vibey_tools/skills/plugins/calculus-geometry-algebra/skills/math-geometry-manifolds-tensors-and-lie-groups/SKILL.md
requires: ["skill-20-riemannian-geometry-1189c0a0d8"]
links: []
---

## §21. Lie Groups and Algebras

**⚠️ A group that is also a smooth manifold — continuous symmetry made differentiable.**
```
SO(3)  rotations in 3D           SU(2)  ⚠️ double covers SO(3) — the quaternion connection
SE(3)  rigid motions             ⚠️ the configuration space of robotics and pose estimation
GL(n)  invertible matrices       SL(n)  determinant 1
```
**Lie algebra `𝔤`** — ⚠️ **the tangent space at the identity, with the Lie bracket.**
**`exp: 𝔤 → G`** maps it back to the group.
**⚠️ Why this matters practically**: **the group is curved and constrained; the algebra is
a vector space.** ⚠️ **Optimization, interpolation and uncertainty are done in the algebra
and mapped back** — **which is exactly why SLAM, robotics and pose estimation use
`se(3)`/`so(3)` rather than optimizing over rotation matrices directly** (see robotics and
computer-vision references).
**⚠️ And Noether's theorem lives here**: continuous symmetries yield conservation laws
(see a Newtonian-mechanics reference §4.5).
