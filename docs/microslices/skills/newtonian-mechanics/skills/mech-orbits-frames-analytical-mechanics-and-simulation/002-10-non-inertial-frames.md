---
id: skill-10-non-inertial-frames-2f0c09b6d0
purpose: 10 non inertial frames
source: src/vibey_tools/skills/plugins/newtonian-mechanics/skills/mech-orbits-frames-analytical-mechanics-and-simulation/SKILL.md
requires: ["skill-9-central-forces-and-orbits-ef54974c4f"]
links: ["skill-11-lagrangian-and-hamiltonian-mechanics-b2f24e954f"]
---

## §10. Non-Inertial Frames

**⚠️ `F = ma` is false in an accelerating frame.** You can rescue it by adding **fictitious
(inertial) forces** — real in their effects within that frame, absent in an inertial one.
```
Linear acceleration:  F_fict = −ma_frame
Centrifugal:          F = mω²r  (outward)
Coriolis:             F = −2m(ω × v)   ⚠️ acts only on bodies MOVING in the frame
Euler:                from angular acceleration of the frame
```
**⚠️ The Coriolis force is the interesting one.** It deflects moving objects — **right in
the northern hemisphere, left in the southern** — and it governs **cyclone rotation, ocean
gyres, and long-range ballistics.**

> **⚠️ GOTCHA — Coriolis does not determine which way your bathtub drains.** ⚠️ **The
> effect at that scale is many orders of magnitude smaller than residual water motion,
> basin asymmetry, and how you pulled the plug.** **It's a genuine effect and a bogus
> example**, and the bogus version is very widely repeated.

**⚠️ The Earth is a rotating frame**, so strictly it's non-inertial: measured `g` varies
with latitude (⚠️ **centrifugal reduction at the equator plus the equatorial bulge**), and
a **Foucault pendulum** visibly demonstrates the rotation.

---
