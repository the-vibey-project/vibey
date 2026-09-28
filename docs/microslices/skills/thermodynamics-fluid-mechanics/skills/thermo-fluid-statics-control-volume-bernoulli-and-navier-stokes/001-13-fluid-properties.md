---
id: skill-13-fluid-properties-b3adcf22db
purpose: 13 fluid properties
source: src/vibey_tools/skills/plugins/thermodynamics-fluid-mechanics/skills/thermo-fluid-statics-control-volume-bernoulli-and-navier-stokes/SKILL.md
requires: []
links: ["skill-14-statics-08206264b4"]
---

## §13. Fluid Properties

```
⚠️ CONTINUUM ASSUMPTION  valid when the Knudsen number Kn = λ/L ≪ 1.
   ⚠️ Breaks down in rarefied gas (high altitude, vacuum) and
   microfluidics — where you need slip models or DSMC
VISCOSITY μ    ⚠️ resistance to shear. Newtonian: τ = μ(du/dy)
   ⚠️ Gas viscosity RISES with temperature; liquid viscosity FALLS.
   Different mechanisms — momentum exchange vs intermolecular forces
KINEMATIC ν = μ/ρ    "momentum diffusivity"
SURFACE TENSION  ⚠️ dominates at small scale; Δp = 2σ/R for a droplet
COMPRESSIBILITY  ⚠️ bulk modulus; a liquid is nearly incompressible
VAPOUR PRESSURE  ⚠️ the cavitation criterion (§24)
```
**⚠️ Non-Newtonian fluids are the norm outside textbooks**: **shear-thinning
(paint, blood, polymer solutions), shear-thickening (cornstarch suspension),
Bingham plastic (toothpaste, drilling mud — ⚠️ requires a yield stress before it flows at
all), and viscoelastic.**

---
