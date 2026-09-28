---
id: skill-6-equations-of-state-ff86e555d7
purpose: 6 equations of state
source: src/vibey_tools/skills/plugins/thermodynamics-fluid-mechanics/skills/thermo-laws-entropy-property-relations-and-phase-behaviour/SKILL.md
requires: ["skill-5-property-relations-0da03a2da2"]
links: ["skill-7-phase-behaviour-c4a5b7f7ff"]
---

## §6. Equations of State

```
IDEAL GAS      Pv = RT. ⚠️ Assumes point particles, no intermolecular forces.
   ⚠️ Good at LOW pressure and HIGH temperature relative to critical
COMPRESSIBILITY FACTOR  Z = Pv/RT. ⚠️ Z = 1 is ideal; the deviation tells
   you how wrong the ideal assumption is
VAN DER WAALS  ⚠️ adds molecular volume (b) and attraction (a). Qualitatively
   right, quantitatively mediocre — and historically important for
   predicting the critical point
CUBIC EOS      ⚠️ Redlich-Kwong, Soave-RK, Peng-Robinson. The practical
   workhorses in process engineering
⚠️ PRINCIPLE OF CORRESPONDING STATES  gases at the same REDUCED
   temperature and pressure (T/T_crit, P/P_crit) behave similarly.
   ⚠️ Remarkable, and the basis of generalized charts
```
**⚠️ For liquids and solids, use tabulated properties or incompressible approximations** —
⚠️ **the ideal gas law is not a general-purpose tool and applying it near saturation is a
classic error.**

---
