---
id: skill-20-internal-flow-1c776573e2
purpose: 20 internal flow
source: src/vibey_tools/skills/plugins/thermodynamics-fluid-mechanics/skills/thermo-dimensional-analysis-flows-turbulence-and-turbomachinery/SKILL.md
requires: ["skill-19-dimensional-analysis-3c3732957e"]
links: ["skill-21-external-flow-and-drag-ab5dfc5de8"]
---

## §20. Internal Flow

```
ENTRANCE LENGTH → fully developed
⚠️ TRANSITION in pipes  Re ≈ 2300 (laminar) to ~4000 (turbulent)
LAMINAR       ⚠️ Hagen-Poiseuille: Q ∝ ΔP·D⁴  — the FOURTH power of diameter.
   ⚠️ Halving the diameter cuts flow 16× at fixed pressure. This dominates
   biological and microfluidic design
⚠️ DARCY-WEISBACH  h_f = f(L/D)(V²/2g)
   ⚠️ f = 64/Re laminar; from Colebrook/Moody for turbulent
MOODY CHART   ⚠️ f vs Re and relative roughness ε/D.
   ⚠️ In fully rough turbulent flow, f becomes INDEPENDENT of Re
MINOR LOSSES  ⚠️ fittings, bends, valves, entries — often NOT minor, and
   frequently dominant in short piping runs
```
**⚠️ Note the friction-factor confusion**: ⚠️ **the Darcy friction factor is 4× the Fanning
friction factor**, **and mixing them up is a classic and expensive unit error.**

---
