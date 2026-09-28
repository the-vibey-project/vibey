---
id: skill-28-quick-reference-633c11751a
purpose: 28 quick reference
source: src/vibey_tools/skills/plugins/medicine-design-software-development/skills/drugdev-reference/SKILL.md
requires: ["skill-27-tools-and-resources-67a142893d"]
links: ["skill-29-method-1cefc60924"]
---

## §28. Quick Reference

### 28.1 Picker
| Question | Where |
|---|---|
| My model has great metrics — is it real? | ⚠️ **Check the split first** (§7 → `drugdev-representation-cheminformatics-data-quality-and-leakage`) |
| What baseline should I beat? | ⚠️ **Random forest on ECFP4** (§13 → `drugdev-qsar-admet-generative-models-and-validation`, §17 → `drugdev-qsar-admet-generative-models-and-validation`) |
| How accurate can this model possibly be? | ⚠️ **The experimental noise floor** (§6 → `drugdev-representation-cheminformatics-data-quality-and-leakage`) |
| Should I use docking scores to rank? | ⚠️ **No. Triage only** (§10 → `drugdev-protein-structure-docking-and-molecular-dynamics`) |
| I need affinity predictions for a series | ⚠️ **FEP, with a good structure** (§12 → `drugdev-protein-structure-docking-and-molecular-dynamics`) |
| Can I dock into an AlphaFold model? | ⚠️ **You can; expect worse performance** (§9 → `drugdev-protein-structure-docking-and-molecular-dynamics`) |
| Generative model outputs look great | ⚠️ **Check synthesizability and objective hacking** (§15 → `drugdev-qsar-admet-generative-models-and-validation`) |
| Which compounds should we make next? | ⚠️ **Active learning with uncertainty** (§16 → `drugdev-qsar-admet-generative-models-and-validation`) |
| How do I join two chemical datasets? | ⚠️ **Standardize, then InChIKey** (§4 → `drugdev-representation-cheminformatics-data-quality-and-leakage`) |
| Model works in-house, fails on new chemistry | ⚠️ **Applicability domain** (§7 → `drugdev-representation-cheminformatics-data-quality-and-leakage`) |
| Will this need to be validated? | ⚠️ **Ask now, not later** (§22 → `drugdev-pipeline-engineering-compute-and-regulated-software`) |
| Does the FDA guidance apply to us? | ⚠️ **Depends on context of use** (§24.2) |

### 28.2 Before you trust a model
- [ ] ⚠️ **Split is scaffold-based or time-based, and justified** (§7 → `drugdev-representation-cheminformatics-data-quality-and-leakage`)
- [ ] ⚠️ **Duplicates removed after canonicalization** (§4 → `drugdev-representation-cheminformatics-data-quality-and-leakage`)
- [ ] Standardization done AFTER splitting, or identically to both (§7 → `drugdev-representation-cheminformatics-data-quality-and-leakage`)
- [ ] ⚠️ **Simple fingerprint baseline run and reported** (§17 → `drugdev-qsar-admet-generative-models-and-validation`)
- [ ] Performance compared against the experimental noise floor (§6 → `drugdev-representation-cheminformatics-data-quality-and-leakage`)
- [ ] ⚠️ **Applicability domain defined and enforced at inference** (§7 → `drugdev-representation-cheminformatics-data-quality-and-leakage`)
- [ ] Uncertainty estimates present and calibrated (§16 → `drugdev-qsar-admet-generative-models-and-validation`)
- [ ] ⚠️ **Activity cliff performance reported separately if relevant** (§13 → `drugdev-qsar-admet-generative-models-and-validation`)
- [ ] ⚠️ **Prospective test planned, and failures will be recorded** (§18 → `drugdev-qsar-admet-generative-models-and-validation`)
- [ ] Model version, data version and environment pinned (§21 → `drugdev-pipeline-engineering-compute-and-regulated-software`)

---
