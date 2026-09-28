---
id: skill-29-quick-reference-53a2320991
purpose: 29 quick reference
source: src/vibey_tools/skills/plugins/refrigeration-ac-climate-control-food-water/skills/hvacr-reference/SKILL.md
requires: ["skill-28-books-and-standards-cabeb684b9"]
links: ["skill-30-method-e2e643724a"]
---

## §29. Quick Reference

### 29.1 Diagnostic picker
| Symptom | Where |
|---|---|
| Not cooling enough | ⚠️ **Superheat + subcooling before anything else** (§5 → `hvacr-cycle-components-refrigerants-and-diagnosis`) |
| High superheat, low subcooling | ⚠️ **Undercharge — find the leak** (§5 → `hvacr-cycle-components-refrigerants-and-diagnosis`) |
| Low superheat, high subcooling | ⚠️ **Overcharge** (§5 → `hvacr-cycle-components-refrigerants-and-diagnosis`) |
| Both high | ⚠️ **Restriction** (§5 → `hvacr-cycle-components-refrigerants-and-diagnosis`) |
| Iced evaporator | ⚠️ **Airflow first** (§5 → `hvacr-cycle-components-refrigerants-and-diagnosis`, §8 → `hvacr-load-calculation-air-humidity-and-heat-pumps`) |
| High head pressure | ⚠️ **Dirty condenser, overcharge, non-condensables** (§5 → `hvacr-cycle-components-refrigerants-and-diagnosis`) |
| Cold but clammy building | ⚠️ **Oversized, short-cycling, no dehumidification** (§7 → `hvacr-load-calculation-air-humidity-and-heat-pumps`, §9 → `hvacr-load-calculation-air-humidity-and-heat-pumps`) |
| Some rooms won't condition | ⚠️ **Duct design, ESP, return path** (§8 → `hvacr-load-calculation-air-humidity-and-heat-pumps`) |
| Heat pump bills disappointing | ⚠️ **Resistance backup running. Check controls** (§11 → `hvacr-load-calculation-air-humidity-and-heat-pumps`) |
| Water dripping from the air handler | ⚠️ **Condensate drain or trap** (§9 → `hvacr-load-calculation-air-humidity-and-heat-pumps`) |
| Produce spoiling fast | ⚠️ **Precooling and ethylene separation** (§15 → `hvacr-cold-chain-temperature-limits-and-validation`, §18 → `hvacr-cold-chain-temperature-limits-and-validation`) |
| Load arrived warm | ⚠️ **Was it pre-cooled? Airflow blocked? Door openings?** (§19 → `hvacr-cold-chain-temperature-limits-and-validation`) |
| Frozen product weeping on thaw | ⚠️ **Frozen too slowly, or storage fluctuated** (§17 → `hvacr-cold-chain-temperature-limits-and-validation`) |
| Is this excursion a problem? | ⚠️ **Cumulative time, and MKT for pharma** (§15 → `hvacr-cold-chain-temperature-limits-and-validation`, §20 → `hvacr-cold-chain-temperature-limits-and-validation`) |
| Preserving without a fridge | ⚠️ **Pick a barrier: a_w, pH, heat, oxygen** (§22 → `hvacr-preservation-water-storage-and-treatment`) |
| Is this water safe? | ⚠️ **Match barrier to threat; taste ≠ safe** (§24 → `hvacr-preservation-water-storage-and-treatment`) |

### 29.2 Cold chain checklist
- [ ] ⚠️ **Product AT temperature before loading — the unit maintains** (§19 → `hvacr-cold-chain-temperature-limits-and-validation`)
- [ ] Precooling as fast as possible after harvest (§15 → `hvacr-cold-chain-temperature-limits-and-validation`)
- [ ] ⚠️ **Airflow path unobstructed; load within the red line** (§19 → `hvacr-cold-chain-temperature-limits-and-validation`)
- [ ] Ethylene producers separated from sensitive product (§18 → `hvacr-cold-chain-temperature-limits-and-validation`)
- [ ] ⚠️ **Chilling-injury-sensitive items NOT refrigerated** (§18 → `hvacr-cold-chain-temperature-limits-and-validation`)
- [ ] ⚠️ **Sensors placed where mapping found the worst case** (§20 → `hvacr-cold-chain-temperature-limits-and-validation`)
- [ ] Handoffs and dock time monitored, not just endpoints (§15 → `hvacr-cold-chain-temperature-limits-and-validation`)
- [ ] ⚠️ **Pulp temperature measured, not just supply air** (§19 → `hvacr-cold-chain-temperature-limits-and-validation`)
- [ ] Excursions assessed cumulatively (§15 → `hvacr-cold-chain-temperature-limits-and-validation`, §20 → `hvacr-cold-chain-temperature-limits-and-validation`)

---
