---
id: skill-31-misconceptions-27ee3c0006
purpose: 31 misconceptions
source: src/vibey_tools/skills/plugins/thermodynamics-fluid-mechanics/skills/thermo-reference/SKILL.md
requires: ["skill-30-anti-patterns-dd7d5f06db"]
links: ["skill-32-numbers-39feabc59d"]
---

## §31. Misconceptions

| Misconception | Correction |
|---|---|
| A hot system "contains heat" | ⚠️ **It contains internal energy. Heat is energy in transit** (§1 → `thermo-laws-entropy-property-relations-and-phase-behaviour`) |
| Temperature measures thermal energy | ⚠️ **Intensive vs extensive. A spark vs a bathtub** (§2 → `thermo-laws-entropy-property-relations-and-phase-behaviour`) |
| Entropy is disorder | ⚠️ **Multiplicity / missing information. Disorder fails on cases** (§4 → `thermo-laws-entropy-property-relations-and-phase-behaviour`) |
| Entropy can never decrease | ⚠️ **Locally yes — that's a fridge. Total can't** (§4 → `thermo-laws-entropy-property-relations-and-phase-behaviour`) |
| Better engineering can beat Carnot | ⚠️ **It's set by temperatures alone** (§4 → `thermo-laws-entropy-property-relations-and-phase-behaviour`) |
| COP > 1 violates energy conservation | ⚠️ **You're moving heat, not creating it** (§9 → `thermo-cycles-exergy-combustion-and-psychrometrics`) |
| Efficiency over 100% is impossible | ⚠️ **Condensing boilers, quoted on LHV** (§11 → `thermo-cycles-exergy-combustion-and-psychrometrics`) |
| Enthalpy is a form of energy | ⚠️ **A bookkeeping bundle: u + Pv** (§3 → `thermo-laws-entropy-property-relations-and-phase-behaviour`) |
| Air moves faster over a wing because it must rejoin | ⚠️ **Equal transit time is FALSE** (§16 → `thermo-fluid-statics-control-volume-bernoulli-and-navier-stokes`) |
| Bernoulli explains lift, Newton is the rival | ⚠️ **Both describe the same flow turning** (§16 → `thermo-fluid-statics-control-volume-bernoulli-and-navier-stokes`) |
| Bernoulli applies generally | ⚠️ **Steady, inviscid, incompressible, along a streamline** (§16 → `thermo-fluid-statics-control-volume-bernoulli-and-navier-stokes`) |
| Smooth surfaces always have less drag | ⚠️ **Dimples delay separation; drag crisis** (§18 → `thermo-fluid-statics-control-volume-bernoulli-and-navier-stokes`, §21 → `thermo-dimensional-analysis-flows-turbulence-and-turbomachinery`) |
| Turbulent boundary layers are bad | ⚠️ **They resist separation better** (§18 → `thermo-fluid-statics-control-volume-bernoulli-and-navier-stokes`) |
| Suction pulls fluid | ⚠️ **Ambient pressure pushes. Nothing pulls** (§14 → `thermo-fluid-statics-control-volume-bernoulli-and-navier-stokes`) |
| Insulation always reduces heat loss | ⚠️ **Below critical radius it can increase it** (§25 → `thermo-heat-transfer-conduction-convection-radiation-and-exchangers`) |
| Space is cold, so spacecraft need heating | ⚠️ **Vacuum insulates; rejecting heat is the problem** (§27 → `thermo-heat-transfer-conduction-convection-radiation-and-exchangers`) |
| h is a property of the fluid | ⚠️ **It depends on geometry and flow. That's the problem** (§26 → `thermo-heat-transfer-conduction-convection-radiation-and-exchangers`) |
| More heat flux always means more boiling | ⚠️ **Past CHF the surface burns out** (§28 → `thermo-heat-transfer-conduction-convection-radiation-and-exchangers`) |
| A droplet evaporates fastest on the hottest plate | ⚠️ **Leidenfrost — film boiling insulates** (§28 → `thermo-heat-transfer-conduction-convection-radiation-and-exchangers`) |
| Tacoma Narrows was resonance from vortex shedding | ⚠️ **Better explained as aeroelastic flutter** (§21 → `thermo-dimensional-analysis-flows-turbulence-and-turbomachinery`) |
| Navier-Stokes is solved, we just need computers | ⚠️ **Existence/smoothness is an open problem** (§17 → `thermo-fluid-statics-control-volume-bernoulli-and-navier-stokes`) |
| DNS will replace turbulence models soon | ⚠️ **Work scales ~Re³. Decades away** (§22 → `thermo-dimensional-analysis-flows-turbulence-and-turbomachinery`, §29.1) |
| ML has replaced turbulence modelling | ⚠️ **Still research-phase; 5–10 years to mainstream** (§29.1) |
| "1000× faster CFD" means faster solvers | ⚠️ **Usually surrogates, valid only in-distribution** (§29.1) |

---
