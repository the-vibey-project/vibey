---
id: skill-29-quick-reference-3b5321079d
purpose: 29 quick reference
source: src/vibey_tools/skills/plugins/manufacturing-mechanical-engineering-for-software-devs/skills/mfg-reference/SKILL.md
requires: ["skill-28-books-6832814b33"]
links: ["skill-30-method-3429315842"]
---

## §29. Quick Reference

### 29.1 Picker
| Question | Where |
|---|---|
| Which process should I use? | ⚠️ **Volume and geometry decide** (§9 → `mfg-process-families-machining-additive-and-moulding`, §19 → `mfg-dfm-metrology-plm-npi-and-what-transfers`) |
| Why is this part so expensive? | ⚠️ **Tolerances, setups, or low volume** (§8 → `mfg-machine-elements-mechanisms-and-tolerances`, §11 → `mfg-process-families-machining-additive-and-moulding`, §19 → `mfg-dfm-metrology-plm-npi-and-what-transfers`) |
| It's strong enough — why did it break? | ⚠️ **Fatigue, or a stress concentration** (§2 → `mfg-mechanics-stress-fatigue-and-materials`, §4 → `mfg-mechanics-stress-fatigue-and-materials`) |
| Assembly binds or warps | ⚠️ **Over-constrained** (§7 → `mfg-machine-elements-mechanisms-and-tolerances`) |
| Parts measure fine but don't fit | ⚠️ **Datum mismatch, or stack-up** (§8 → `mfg-machine-elements-mechanisms-and-tolerances`) |
| Moulded part has sink marks | ⚠️ **Wall thickness. Core it out, rib it** (§14 → `mfg-process-families-machining-additive-and-moulding`) |
| Machined part can't be made | ⚠️ **Internal corners, tool reach, or setups** (§11 → `mfg-process-families-machining-additive-and-moulding`) |
| Should we 3D print it? | ⚠️ **Geometry, consolidation or lead time — else no** (§13 → `mfg-process-families-machining-additive-and-moulding`, §25.1) |
| How do I cut cost? | ⚠️ **Delete parts first** (§17 → `mfg-dfm-metrology-plm-npi-and-what-transfers`) |
| Can I just change the drawing? | ⚠️ **Is it still interchangeable?** (§21 → `mfg-dfm-metrology-plm-npi-and-what-transfers`) |
| FEA says it's fine | ⚠️ **Check boundary conditions; validate physically** (§20 → `mfg-dfm-metrology-plm-npi-and-what-transfers`) |
| Supplier wants an MOQ | ⚠️ **Setup costs are fixed per order** (§19 → `mfg-dfm-metrology-plm-npi-and-what-transfers`, §22 → `mfg-dfm-metrology-plm-npi-and-what-transfers`) |
| What should software steal from this? | ⚠️ **§24 → `mfg-dfm-metrology-plm-npi-and-what-transfers`, and tolerance thinking first** |

### 29.2 Design review checklist
- [ ] ⚠️ **Tolerances justified by FUNCTION, not habit** (§8 → `mfg-machine-elements-mechanisms-and-tolerances`)
- [ ] ⚠️ **Stack-up analysed for every critical fit** (§8 → `mfg-machine-elements-mechanisms-and-tolerances`)
- [ ] Datums consistent between design, manufacture and inspection (§8 → `mfg-machine-elements-mechanisms-and-tolerances`)
- [ ] ⚠️ **Fatigue considered where loading is cyclic** (§4 → `mfg-mechanics-stress-fatigue-and-materials`)
- [ ] Stress concentrations filleted (§2 → `mfg-mechanics-stress-fatigue-and-materials`)
- [ ] ⚠️ **Exactly constrained, not over-constrained** (§7 → `mfg-machine-elements-mechanisms-and-tolerances`)
- [ ] ⚠️ **Manufacturable by the intended process — draft, walls, reach** (§17 → `mfg-dfm-metrology-plm-npi-and-what-transfers`)
- [ ] Assembly possible in one direction, with access (§17 → `mfg-dfm-metrology-plm-npi-and-what-transfers`)
- [ ] ⚠️ **Part count challenged: can any of these be deleted?** (§17 → `mfg-dfm-metrology-plm-npi-and-what-transfers`)
- [ ] Standard parts used wherever possible (§6 → `mfg-machine-elements-mechanisms-and-tolerances`, §22 → `mfg-dfm-metrology-plm-npi-and-what-transfers`)
- [ ] ⚠️ **Dissimilar metals checked for galvanic contact** (§5 → `mfg-mechanics-stress-fatigue-and-materials`)
- [ ] ⚠️ **Interchangeability decided before the revision is released** (§21 → `mfg-dfm-metrology-plm-npi-and-what-transfers`)

---
