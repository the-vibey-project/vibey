---
id: skill-16-bernoulli-and-the-lift-myth-5d87c07053
purpose: 16 bernoulli and the lift myth
source: src/vibey_tools/skills/plugins/thermodynamics-fluid-mechanics/skills/thermo-fluid-statics-control-volume-bernoulli-and-navier-stokes/SKILL.md
requires: ["skill-15-the-control-volume-5fcd89c0f1"]
links: ["skill-17-navier-stokes-7401d82682"]
---

## §16. ⚠️ Bernoulli — and the Lift Myth

```
⚠️ p + ½ρV² + ρgz = constant
⚠️ VALID ONLY: steady, incompressible, inviscid, ALONG A STREAMLINE,
   no shaft work, no heat transfer
```
> **⚠️ GOTCHA — Bernoulli is the most misapplied equation in engineering, and it is
> misapplied by textbooks.** ⚠️ **It does NOT apply across streamlines in general, through
> a pump or turbine, in viscous-dominated regions, or in separated flow.** **⚠️ Applying
> it where viscosity matters gives a confidently wrong answer that looks reasonable.**

> **⚠️ GOTCHA — the "equal transit time" explanation of aerodynamic lift is FALSE, and it
> is still in circulation and in some textbooks.** ⚠️ **The claim that air parting at the
> leading edge must rejoin at the trailing edge — and therefore travels faster over the
> longer upper surface — has no physical basis.** **⚠️ Measured flow shows upper-surface
> air arrives WELL AHEAD of the lower-surface air, not simultaneously.**
> **⚠️ It also cannot explain symmetric aerofoils, flat plates, or inverted flight, all of
> which generate lift perfectly well.**
> **⚠️ The correct account**: **the aerofoil turns the flow downward (circulation, with the
> Kutta condition setting the circulation), and by Newton's third law the reaction is
> lift.** ⚠️ **Bernoulli and the momentum picture are two consistent descriptions of the
> same thing — the error is not "using Bernoulli," it's the equal-transit-time premise.**

**⚠️ Where Bernoulli IS the right tool**: **Pitot-static measurement, venturi and orifice
metering, nozzle exit velocity, Torricelli.** ⚠️ **The extended form with head losses
(§20 → `thermo-dimensional-analysis-flows-turbulence-and-turbomachinery`) is the practical engineering version.**

---
