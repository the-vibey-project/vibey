---
id: skill-10-multiple-view-geometry-e360b169a5
purpose: 10 multiple view geometry
source: src/vibey_tools/skills/plugins/graphics-and-vision/skills/gfx-image-formation-classical-vision-and-geometry/SKILL.md
requires: ["skill-9-classical-computer-vision-35e5debbe6"]
links: []
---

## §10. Multiple View Geometry

**⚠️ This is the mathematical core of 3D vision and it has not changed.**

**Epipolar geometry**: given two views, a point in one image constrains its match to a
**line** in the other.
```
x'ᵀ F x = 0      fundamental matrix, uncalibrated (7 DOF)
x'ᵀ E x = 0      essential matrix, calibrated:  E = Kᵀ F K'
```
**⚠️ `E` decomposes into `R` and `t` — with `t` only up to scale, and four candidate
solutions.** **Cheirality (the requirement that points be in front of both cameras) picks
the right one.** ⚠️ **Monocular reconstruction has an inherent scale ambiguity that no
amount of processing removes — you need a known baseline, an object of known size, or
another sensor.**

**Estimation**: 8-point and normalized 8-point for `F`, **5-point (Nistér)** for `E`,
**PnP** for pose from known 3D-2D correspondences, homography (`H`) for planes or pure
rotation.
**⚠️ Hartley normalization is not optional** — the unnormalized 8-point algorithm is
numerically terrible, and this is one of the best-known "the textbook version fails"
results in the field.

**Triangulation** → 3D points. **Bundle adjustment** — ⚠️ **the global nonlinear
least-squares refinement of all poses and points simultaneously, minimizing reprojection
error.** Sparse Levenberg-Marquardt exploiting the **Schur complement** structure; **Ceres**
and **g2o** are the standard solvers.

**Pipelines**: **SfM** (offline, incremental or global — **COLMAP** is the reference),
**MVS** for dense reconstruction, **visual SLAM** (⚠️ **ORB-SLAM3 as the classical
benchmark; feature-based vs direct methods like DSO/LSD-SLAM**), **VIO** (⚠️ **fusing an
IMU resolves scale and handles fast motion — which is why every practical AR system is
visual-inertial**).

**Stereo**: rectify → disparity → depth (`Z = f·B/d`). ⚠️ **Depth error grows with the
square of distance**, so a stereo rig has a usable range set by its baseline. **SGM
(semi-global matching)** is the classical standard.
