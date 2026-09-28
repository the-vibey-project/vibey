---
id: skill-3-the-first-law-00d548ab88
purpose: 3 the first law
source: src/vibey_tools/skills/plugins/thermodynamics-fluid-mechanics/skills/thermo-laws-entropy-property-relations-and-phase-behaviour/SKILL.md
requires: ["skill-2-the-zeroth-law-and-temperature-856a74221e"]
links: ["skill-4-the-second-law-and-entropy-4954e7540e"]
---

## §3. The First Law

```
CLOSED SYSTEM      ΔU = Q − W
⚠️ CONTROL VOLUME  (steady flow energy equation, SFEE)
   Q̇ − Ẇ = Σṁ_out(h + V²/2 + gz) − Σṁ_in(h + V²/2 + gz)
⚠️ ENTHALPY  h = u + Pv  — ⚠️ NOT a form of energy; a bookkeeping convenience
   that bundles internal energy with the FLOW WORK (Pv) needed to push
   mass across the boundary. It exists because open systems are common
```
**⚠️ Sign conventions vary between textbooks and cause endless errors** — ⚠️ **be explicit
about whether W is work done BY or ON the system.** **Most engineering texts take W as
work done by the system (so it's positive in a turbine).**
**Specific heats**: **c_v and c_p**; ⚠️ **c_p > c_v always, because constant-pressure
heating must also do expansion work.** **For ideal gases, c_p − c_v = R.**

---
