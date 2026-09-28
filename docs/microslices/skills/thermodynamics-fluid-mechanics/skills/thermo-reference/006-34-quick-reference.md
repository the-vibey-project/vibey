---
id: skill-34-quick-reference-512939f591
purpose: 34 quick reference
source: src/vibey_tools/skills/plugins/thermodynamics-fluid-mechanics/skills/thermo-reference/SKILL.md
requires: ["skill-33-books-9e7d10f824"]
links: ["skill-35-method-4d9e2aa8bf"]
---

## §34. Quick Reference

### 34.1 Picker
| Question | Where |
|---|---|
| Where do I start any problem? | ⚠️ **Draw the control volume** (§15 → `thermo-fluid-statics-control-volume-bernoulli-and-navier-stokes`) |
| Does viscosity matter here? | ⚠️ **Reynolds number** (§19 → `thermo-dimensional-analysis-flows-turbulence-and-turbomachinery`) |
| Does compressibility matter? | ⚠️ **Ma > 0.3** (§19 → `thermo-dimensional-analysis-flows-turbulence-and-turbomachinery`, §23 → `thermo-dimensional-analysis-flows-turbulence-and-turbomachinery`) |
| Can I use lumped capacitance? | ⚠️ **Bi < 0.1** (§19 → `thermo-dimensional-analysis-flows-turbulence-and-turbomachinery`, §25 → `thermo-heat-transfer-conduction-convection-radiation-and-exchangers`) |
| Can I use Bernoulli? | ⚠️ **Steady, inviscid, incompressible, one streamline** (§16 → `thermo-fluid-statics-control-volume-bernoulli-and-navier-stokes`) |
| Best possible cycle efficiency? | ⚠️ **1 − T_C/T_H, absolute temperatures** (§4 → `thermo-laws-entropy-property-relations-and-phase-behaviour`) |
| Where are my real losses? | ⚠️ **Exergy analysis, not First Law efficiency** (§10 → `thermo-cycles-exergy-combustion-and-psychrometrics`) |
| Why is my heat exchanger underperforming? | ⚠️ **Fouling; check flow arrangement** (§28 → `thermo-heat-transfer-conduction-convection-radiation-and-exchangers`) |
| Pump is noisy and eroding | ⚠️ **Cavitation. Check NPSH available** (§24 → `thermo-dimensional-analysis-flows-turbulence-and-turbomachinery`) |
| Flow separates / stalls | ⚠️ **Adverse pressure gradient; consider tripping it turbulent** (§18 → `thermo-fluid-statics-control-volume-bernoulli-and-navier-stokes`) |
| Heat won't leave a small hot chip | ⚠️ **Contact resistance, then h magnitude** (§25 → `thermo-heat-transfer-conduction-convection-radiation-and-exchangers`, §26 → `thermo-heat-transfer-conduction-convection-radiation-and-exchangers`) |
| Air cooling isn't enough | ⚠️ **§29.2's thresholds** |
| Which turbulence model? | ⚠️ **RANS to iterate; scale-resolving where it separates** (§22 → `thermo-dimensional-analysis-flows-turbulence-and-turbomachinery`, §29.1) |
| Evaporative cooling not working | ⚠️ **Wet-bulb is the floor** (§12 → `thermo-cycles-exergy-combustion-and-psychrometrics`) |

### 34.2 Before trusting a result
- [ ] ⚠️ **Control volume drawn; every crossing accounted** (§15 → `thermo-fluid-statics-control-volume-bernoulli-and-navier-stokes`)
- [ ] ⚠️ **Absolute temperatures and pressures where required** (§4 → `thermo-laws-entropy-property-relations-and-phase-behaviour`, §14 → `thermo-fluid-statics-control-volume-bernoulli-and-navier-stokes`)
- [ ] Assumptions of every formula checked against the actual regime (§16 → `thermo-fluid-statics-control-volume-bernoulli-and-navier-stokes`)
- [ ] ⚠️ **Dimensionless groups computed BEFORE the detailed calculation** (§19 → `thermo-dimensional-analysis-flows-turbulence-and-turbomachinery`)
- [ ] Units consistent; Darcy vs Fanning, HHV vs LHV resolved (§20 → `thermo-dimensional-analysis-flows-turbulence-and-turbomachinery`, §11 → `thermo-cycles-exergy-combustion-and-psychrometrics`)
- [ ] ⚠️ **Second Law sanity check — is entropy generation ≥ 0?** (§4 → `thermo-laws-entropy-property-relations-and-phase-behaviour`)
- [ ] ⚠️ **Order-of-magnitude estimate agrees with the computed answer**
- [ ] ⚠️ **CFD validated against experiment, not just converged** (§29.1)

---
