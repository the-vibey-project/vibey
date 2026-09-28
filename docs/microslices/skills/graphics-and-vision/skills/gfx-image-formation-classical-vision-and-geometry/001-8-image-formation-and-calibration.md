---
id: skill-8-image-formation-and-calibration-ea1be9776e
purpose: 8 image formation and calibration
source: src/vibey_tools/skills/plugins/graphics-and-vision/skills/gfx-image-formation-classical-vision-and-geometry/SKILL.md
requires: []
links: ["skill-9-classical-computer-vision-35e5debbe6"]
---

## §8. Image Formation and Calibration

**The pinhole model** — the shared foundation of §1 → `gfx-transforms-rasterization-and-rendering` and everything in vision:
```
        [fx  s  cx]
K =     [0  fy  cy]        x = K [R | t] X
        [0   0   1]
```
**`K` is intrinsics** (focal lengths in pixels, principal point, skew — ⚠️ **skew is
essentially always 0 in real cameras**); **`[R|t]` is extrinsics** (pose).

**⚠️ Distortion is not in that model and must be handled separately**: radial
(`k1, k2, k3` — barrel/pincushion) and tangential (`p1, p2`). **Fisheye and wide-angle
need a different model entirely** (equidistant, Kannala-Brandt) — ⚠️ **applying the
polynomial radial model to a fisheye lens fails badly.**

**Calibration**: **Zhang's method** — a planar checkerboard at multiple orientations,
solve for `K` and distortion, refine by bundle adjustment.
**⚠️ The practical failures**: too few orientations (⚠️ **you need real tilt, not just
translation, or focal length and distance are unseparable**), the board not covering the
image corners (⚠️ **where distortion is largest, so it goes unconstrained**), a non-flat
printed target, and **rolling shutter** on a moving camera.

**Sensor realities**: **Bayer pattern** and demosaicing, rolling vs global shutter
(⚠️ **rolling shutter skews moving objects and breaks the rigid-projection assumption
underlying SfM**), exposure and noise (photon/shot noise is Poisson — ⚠️ **noise scales
with the square root of signal, which is why dark regions are noisier**), and **the ISP
pipeline**, which has usually already applied sharpening, denoising and tone curves before
you see the image.

---
