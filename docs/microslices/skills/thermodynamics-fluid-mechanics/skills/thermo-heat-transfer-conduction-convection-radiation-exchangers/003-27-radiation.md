---
id: skill-27-radiation-c400c104b0
purpose: 27 radiation
source: src/vibey_tools/skills/plugins/thermodynamics-fluid-mechanics/skills/thermo-heat-transfer-conduction-convection-radiation-exchangers/SKILL.md
requires: ["skill-26-convection-40289a504c"]
links: ["skill-28-heat-exchangers-and-phase-change-e5bed044e9"]
---

## §27. Radiation

```
⚠️ STEFAN-BOLTZMANN  q" = εσT⁴   (σ = 5.67×10⁻⁸ W/m²K⁴)
   ⚠️ FOURTH POWER of ABSOLUTE temperature — which is why radiation is
   negligible at room temperature and dominant in furnaces and in space
EMISSIVITY ε · ABSORPTIVITY α · ⚠️ Kirchhoff: α = ε at the same wavelength
   and temperature
VIEW FACTOR F₁₂   ⚠️ geometry. Reciprocity: A₁F₁₂ = A₂F₂₁
WIEN'S LAW        λ_max·T ≈ 2898 μm·K — where the peak sits
```
**⚠️ Selective surfaces exploit the spectral difference**: ⚠️ **a solar absorber wants high
absorptivity in the visible (where the sun emits) and low emissivity in the infrared
(where it would re-radiate)** — **not a contradiction of Kirchhoff, because those are
different wavelengths.**
**⚠️ In space, radiation is the ONLY heat rejection mechanism** — **no convection, no
conduction to anything** — ⚠️ **which is why spacecraft thermal design is dominated by
radiator area and why "space is cold" is misleading: vacuum is a superb insulator, and
overheating is usually the harder problem.**

---
