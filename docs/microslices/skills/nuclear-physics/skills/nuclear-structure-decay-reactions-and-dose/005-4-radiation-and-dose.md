---
id: skill-4-radiation-and-dose-91a407b0bd
purpose: 4 radiation and dose
source: src/vibey_tools/skills/plugins/nuclear-physics/skills/nuclear-structure-decay-reactions-and-dose/SKILL.md
requires: ["skill-3-reactions-and-cross-sections-15f759a305"]
links: []
---

## §4. Radiation and Dose

| Type | Range in matter | ⚠️ Hazard |
|---|---|---|
| **Alpha** | ⚠️ **cm of air; stopped by skin/paper** | ⚠️ **Negligible externally; severe INTERNALLY (inhaled/ingested)** |
| **Beta** | mm of plastic | Skin and eye dose; internal |
| **Gamma/X** | ⚠️ **attenuates exponentially — no definite range** | Whole-body penetrating |
| **Neutron** | Needs hydrogenous shielding | ⚠️ **Highly damaging; activates materials** |

**⚠️ Shielding logic follows the interaction mechanism**: **hydrogen-rich material
(water, polyethylene, concrete) to moderate neutrons, then a thermal absorber (boron);
high-Z material (lead) for gamma.** ⚠️ **High-Z alone is poor for neutrons, and moderating
material alone is poor for gamma. Layered shields are the norm.**

**Dose quantities — routinely muddled:**
```
Activity     becquerel (Bq)   ⚠️ decays/second — a property of the SOURCE
Absorbed     gray (Gy)        J/kg deposited
Equivalent   sievert (Sv)     ⚠️ Gy × radiation weighting (α ≈ 20, γ/β = 1)
Effective    sievert          ⚠️ × tissue weighting — whole-body risk proxy
```
**⚠️ Bq tells you nothing about hazard on its own.** **A large Bq number from a weak
alpha emitter safely contained is harmless; a small number inhaled is not.** **Reporting
becquerels without geometry, isotope and pathway is uninformative.**

**⚠️ Deterministic vs stochastic effects — the distinction that governs everything:**
- **Deterministic** — ⚠️ **have a threshold, severity rises with dose.** Radiation
  sickness, burns, cataracts. **Below threshold, they do not occur.**
- **Stochastic** — ⚠️ **cancer risk; probability rises with dose, severity does not.**
  **Assumed by regulation to have no threshold (LNT), which is a conservative policy
  choice and is scientifically contested at low doses** (§15 → `nuclear-reference`).

**ALARA**: **time, distance** (⚠️ **inverse square — the cheapest control by far**),
**shielding**.
