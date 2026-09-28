---
id: skill-2-airfoils-and-wings-6c92ffbfd7
purpose: 2 airfoils and wings
source: src/vibey_tools/skills/plugins/aerospace-engineering/skills/aero-aerodynamics-airfoils-and-compressible-flow/SKILL.md
requires: ["skill-1-aerodynamics-fundamentals-b5af570daf"]
links: ["skill-3-drag-18130cc648"]
---

## §2. Airfoils and Wings

**Geometry**: chord, camber, thickness, leading-edge radius. **NACA series** (⚠️ **4-digit
digits literally encode camber, camber position and thickness**), supercritical
(⚠️ **flattened upper surface delays shock formation — §4**), laminar-flow sections.

**`C_L` vs angle of attack** is linear until stall.
> **⚠️ GOTCHA — stall is a function of ANGLE OF ATTACK, not airspeed.** ⚠️ **An aircraft
> can stall at any speed and any attitude.** **The "stall speed" in the manual is the
> speed at which 1g level flight requires the critical AoA — change the load factor and
> it changes: `V_stall ∝ √n`.** **A 2g turn raises stall speed by ~41%.** ⚠️ **This
> misconception has killed people, which is why AoA indicators exist and why stall
> warning is AoA-based.**

**⚠️ Finite wings differ fundamentally from 2D airfoils**: **pressure equalization at the
tips creates trailing vortices, which induce a downwash, which tilts the local lift vector
backwards.** ⚠️ **That backwards component IS induced drag — it is the unavoidable price
of generating lift with a finite wing** (§3).
```
Aspect ratio AR = b²/S     ⚠️ high AR = low induced drag (gliders, airliners)
                            low AR = structurally light, manoeuvrable (fighters)
Elliptical lift distribution ⚠️ minimizes induced drag — the Spitfire's famous rationale
Taper, sweep, twist (washout — ⚠️ makes the root stall first, preserving aileron authority)
```
**High-lift devices**: flaps (⚠️ **increase camber and sometimes area**), slats
(⚠️ **re-energize the boundary layer to delay separation to higher AoA**), and the
resulting trade of `C_L,max` against drag.

---
