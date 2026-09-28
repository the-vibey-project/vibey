---
id: skill-19-dimensional-analysis-3c3732957e
purpose: 19 dimensional analysis
source: src/vibey_tools/skills/plugins/thermodynamics-fluid-mechanics/skills/thermo-dimensional-analysis-flows-turbulence-and-turbomachinery/SKILL.md
requires: []
links: ["skill-20-internal-flow-1c776573e2"]
---

## §19. ⚠️ Dimensional Analysis

**⚠️ The highest-leverage tool in the subject. Buckingham Pi: a relation among n variables
with k independent dimensions reduces to n−k dimensionless groups.**
```
⚠️ REYNOLDS   Re = ρVL/μ   inertia/viscous. ⚠️ THE master parameter
⚠️ MACH       Ma = V/c     compressibility. ⚠️ >0.3 matters, >1 changes everything
⚠️ FROUDE     Fr = V/√(gL) inertia/gravity — free surface, ships, open channel
⚠️ PRANDTL    Pr = ν/α     momentum vs thermal diffusivity (§26)
⚠️ NUSSELT    Nu = hL/k    convective vs conductive heat transfer — the OUTPUT
⚠️ BIOT       Bi = hL/k_s  ⚠️ note k is the SOLID's here, unlike Nusselt.
              Bi < 0.1 justifies lumped capacitance (§25)
⚠️ RAYLEIGH   Ra = Gr·Pr   natural convection driver
⚠️ WEBER      We = ρV²L/σ  inertia/surface tension — droplets, atomization
⚠️ STROUHAL   St = fL/V    vortex shedding frequency
⚠️ FOURIER    Fo = αt/L²   dimensionless time in transient conduction
```
**⚠️ Dynamic similarity is what makes model testing possible**: ⚠️ **match the relevant
dimensionless groups and the model predicts the prototype.** **⚠️ The practical difficulty
is that you often cannot match all of them at once — matching Reynolds and Froude
simultaneously in ship testing requires an impossible fluid, which is why hull resistance
is decomposed into components scaled separately.**
**⚠️ Use them before computing anything**: ⚠️ **Re tells you whether viscosity matters, Ma
whether compressibility does, Bi whether internal gradients do.** **Knowing which terms
are negligible is most of engineering judgement.**

---
