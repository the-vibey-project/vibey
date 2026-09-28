---
id: skill-1-kinematics-5c770f960e
purpose: 1 kinematics
source: src/vibey_tools/skills/plugins/newtonian-mechanics/skills/mech-kinematics-newtons-laws-and-forces/SKILL.md
requires: ["skill-0-routing-2a0bf50fb4"]
links: ["skill-2-newton-s-laws-ea158a6436"]
---

## §1. Kinematics

**Description of motion, before any mention of cause.**
```
v = dr/dt        a = dv/dt = d²r/dt²
Constant acceleration only:
  v = v₀ + at        r = r₀ + v₀t + ½at²        v² = v₀² + 2a·Δr
```
> **⚠️ GOTCHA — those three equations are valid only for constant acceleration**, and
> students apply them everywhere. **The moment `a` depends on position (a spring), on
> velocity (drag), or on time, they are wrong.** ⚠️ **The general case requires
> integrating the differential equation** — which is why §14 → `mech-orbits-frames-analytical-mechanics-and-simulation` exists.

**⚠️ Velocity and acceleration are independent.** A body can have zero velocity and
nonzero acceleration (**a ball at the top of its arc — this is the classic exam
question**), or constant speed and nonzero acceleration (**uniform circular motion**).

**Circular motion**: `a_c = v²/r = ω²r`, directed **toward the centre**. Angular
quantities `θ, ω, α` mirror the linear ones exactly.

**Projectile motion**: horizontal and vertical decouple (⚠️ **without drag — with drag they
couple, and there is no closed-form solution; see §3.4**). Range on level ground is
`v₀² sin(2θ)/g`, maximum at 45°.

**⚠️ Relative motion**: `v_AC = v_AB + v_BC`. **Galilean velocity addition**, and it's
exactly what special relativity replaces.

---
