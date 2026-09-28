---
id: skill-17-navier-stokes-7401d82682
purpose: 17 navier stokes
source: src/vibey_tools/skills/plugins/thermodynamics-fluid-mechanics/skills/thermo-fluid-statics-control-volume-bernoulli-and-navier-stokes/SKILL.md
requires: ["skill-16-bernoulli-and-the-lift-myth-5d87c07053"]
links: ["skill-18-boundary-layers-eca1ca34f7"]
---

## §17. Navier-Stokes

```
⚠️ ρ(∂V/∂t + V·∇V) = −∇p + μ∇²V + ρg
   unsteady + convective  =  pressure + viscous + body force
```
**⚠️ The convective term V·∇V is nonlinear, and that nonlinearity is the source of
essentially all the difficulty** — **turbulence, chaos, and the fact that existence and
smoothness in 3D remains a Millennium Prize problem.**
**⚠️ Exact solutions exist only for a handful of highly restricted cases** — **Couette,
Poiseuille, Stokes flow** — **which is why the subject is dominated by dimensional
analysis (§19 → `thermo-dimensional-analysis-flows-turbulence-and-turbomachinery`), empirical correlation, and computation (§29.1 → `thermo-reference`).**
**⚠️ Useful limits**: ⚠️ **Stokes flow (Re ≪ 1) drops the convective term entirely — linear,
reversible, and the regime of microorganisms and sedimentation; potential flow (inviscid,
irrotational) is analytically tractable and ⚠️ produces d'Alembert's paradox — zero drag —
which is precisely how we learned viscosity is never negligible near a wall** (§18).

---
