---
id: skill-9-refrigeration-and-heat-pumps-2c4a00abe5
purpose: 9 refrigeration and heat pumps
source: src/vibey_tools/skills/plugins/thermodynamics-fluid-mechanics/skills/thermo-cycles-exergy-combustion-and-psychrometrics/SKILL.md
requires: ["skill-8-power-cycles-f575324fd6"]
links: ["skill-10-exergy-24f618d16e"]
---

## §9. Refrigeration and Heat Pumps

**⚠️ A heat engine run backwards: work in, heat moved from cold to hot.**
```
⚠️ COP_refrigeration = Q_C/W        ⚠️ COP_heat pump = Q_H/W = COP_R + 1
⚠️ Carnot limits: COP_R = T_C/(T_H−T_C)    COP_HP = T_H/(T_H−T_C)
```
**⚠️ COP exceeds 1 routinely, and this confuses people** — ⚠️ **it is not an efficiency and
does not violate anything.** **You're MOVING heat, not creating it, so getting 3–4 units of
heat delivered per unit of work is ordinary.** ⚠️ **This is the entire thermodynamic case
for heat pumps over resistance heating.**
**⚠️ The vapour-compression cycle**: **evaporator → compressor → condenser → expansion
valve.** ⚠️ **The expansion valve is deliberately irreversible (throttling, isenthalpic) —
a turbine would recover work but isn't worth the cost and complexity at small scale.**
**⚠️ COP collapses as the temperature lift grows** — **which is why air-source heat pumps
degrade in extreme cold and why ground-source performs better.**
**⚠️ Absorption refrigeration** — **driven by heat rather than work; useful where waste
heat is free.**

---
