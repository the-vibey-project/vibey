---
id: skill-4-compressible-and-supersonic-flow-3c4282e70a
purpose: 4 compressible and supersonic flow
source: src/vibey_tools/skills/plugins/aerospace-engineering/skills/aero-aerodynamics-airfoils-and-compressible-flow/SKILL.md
requires: ["skill-3-drag-18130cc648"]
links: []
---

## §4. Compressible and Supersonic Flow

**⚠️ Below M ≈ 0.3, air is effectively incompressible. Above it, density changes matter.**
```
Subsonic     M < 0.8      Transonic  0.8–1.2  ⚠️ THE hard regime — mixed subsonic and
                                     supersonic flow, shocks forming on the wing
Supersonic   1.2–5        Hypersonic M > 5    ⚠️ real gas effects, dissociation
```
**⚠️ Shock waves** — discontinuous jumps in pressure, density and temperature.
**Normal shocks** are always to subsonic downstream; **oblique** turn the flow;
**expansion fans** (Prandtl-Meyer) accelerate it.
**⚠️ Critical Mach number** is where flow first reaches M=1 somewhere on the wing;
**drag divergence** follows as shocks form and cause wave drag and shock-induced
separation.

**⚠️ The transonic fixes, and each has a clear physical reason**: **swept wings**
(⚠️ **only the velocity component normal to the leading edge matters, so sweep effectively
reduces it**), **supercritical airfoils**, **area ruling** (⚠️ **the "Coke bottle" fuselage
— smooth the total cross-sectional area distribution and transonic drag falls
dramatically**).

**⚠️ Aerodynamic centre shifts aft** from ~25% chord subsonically to ~50% supersonically —
⚠️ **which produces a large nose-down trim change and is why Concorde pumped fuel between
tanks to move its CG.**

**Hypersonics**: ⚠️ **aerodynamic heating scales roughly with `V³`, which is why reentry is
a thermal problem rather than a drag problem** (see a rocket-science reference).
