---
id: skill-25-conduction-a988553c88
purpose: 25 conduction
source: src/vibey_tools/skills/plugins/thermodynamics-fluid-mechanics/skills/thermo-heat-transfer-conduction-convection-radiation-and-exchangers/SKILL.md
requires: []
links: ["skill-26-convection-cc455949fc"]
---

## §25. Conduction

```
⚠️ FOURIER'S LAW   q" = −k∇T
1D PLANE WALL      R = L/(kA)     CYLINDER  R = ln(r₂/r₁)/(2πkL)
⚠️ THERMAL RESISTANCE NETWORKS — series and parallel, exactly like circuits.
   ⚠️ The most useful practical tool in conduction
FINS               ⚠️ fin efficiency; adding area helps only if the fin
   conducts well relative to the convection removing heat from it
⚠️ TRANSIENT       lumped capacitance valid when Bi < 0.1 (§19);
   otherwise Heisler charts or the semi-infinite solution
⚠️ CONTACT RESISTANCE  real interfaces are not perfect. ⚠️ Frequently the
   dominant resistance in electronics cooling — hence thermal interface
   materials (§29.2)
```
**⚠️ Critical radius of insulation is the counterintuitive one**: ⚠️ **adding insulation to
a small-diameter pipe or wire can INCREASE heat loss**, **because the added outer surface
area can outweigh the added conductive resistance.** **Above the critical radius,
insulation behaves as expected.**

---
