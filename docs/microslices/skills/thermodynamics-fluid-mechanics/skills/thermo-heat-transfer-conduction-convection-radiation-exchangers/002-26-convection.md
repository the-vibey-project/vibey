---
id: skill-26-convection-40289a504c
purpose: 26 convection
source: src/vibey_tools/skills/plugins/thermodynamics-fluid-mechanics/skills/thermo-heat-transfer-conduction-convection-radiation-exchangers/SKILL.md
requires: ["skill-25-conduction-dc284d7605"]
links: ["skill-27-radiation-c400c104b0"]
---

## §26. Convection

**⚠️ q = hA(T_s − T_∞) — and h is not a property.** ⚠️ **The heat transfer coefficient
depends on geometry, flow regime, fluid properties and velocity, and finding it is the
whole problem.**
```
FORCED     ⚠️ Nu = f(Re, Pr). Dittus-Boelter for turbulent pipe flow;
   many geometry-specific correlations
NATURAL    ⚠️ Nu = f(Ra, Pr). Buoyancy-driven, and much weaker than forced
MIXED      ⚠️ when Gr/Re² ~ 1, neither dominates
```
**⚠️ Typical magnitudes of h span orders of magnitude, and knowing the ranges is more
useful than any single correlation** (§32 → `thermo-reference`) — ⚠️ **natural convection in air is feeble;
boiling and condensation are enormous.** **⚠️ This ordering is exactly why §29.2 → `thermo-reference` happened.**
**⚠️ The Prandtl number tells you the relative thickness of the velocity and thermal
boundary layers**: ⚠️ **Pr ≪ 1 (liquid metals) means thermal layer much thicker; Pr ≫ 1
(oils) the reverse.**

---
