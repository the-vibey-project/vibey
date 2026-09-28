---
id: skill-18-boundary-layers-eca1ca34f7
purpose: 18 boundary layers
source: src/vibey_tools/skills/plugins/thermodynamics-fluid-mechanics/skills/thermo-fluid-statics-control-volume-bernoulli-and-navier-stokes/SKILL.md
requires: ["skill-17-navier-stokes-7401d82682"]
links: []
---

## §18. Boundary Layers

**⚠️ Prandtl's 1904 insight is the one that made modern fluid mechanics possible**:
⚠️ **viscous effects are confined to a thin layer near the surface; outside it, inviscid
theory works.** **This reconciled d'Alembert's paradox with reality and split an
intractable problem into two tractable ones.**
```
⚠️ NO-SLIP CONDITION  fluid velocity at a solid wall equals the wall's
   velocity. ⚠️ The boundary condition that makes viscosity matter at all
δ (thickness), δ* (displacement), θ (momentum thickness)
⚠️ TRANSITION  laminar → turbulent, around Re_x ~ 5×10⁵ on a flat plate
   (⚠️ highly sensitive to roughness, freestream turbulence, pressure gradient)
⚠️ SEPARATION  an ADVERSE pressure gradient (dp/dx > 0) decelerates the
   near-wall fluid until it reverses. ⚠️ Separation causes pressure drag,
   stall and most of the hard problems in aerodynamics
```
**⚠️ The counterintuitive result worth knowing**: ⚠️ **a TURBULENT boundary layer resists
separation better than a laminar one, because turbulent mixing brings high-momentum fluid
toward the wall.** **⚠️ This is why golf balls have dimples — tripping the boundary layer
turbulent increases skin friction slightly but delays separation dramatically, shrinking
the wake and cutting total drag.** **Same reason for turbulator strips and vortex
generators.**
