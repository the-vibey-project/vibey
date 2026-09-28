---
id: skill-25-misconceptions-96b1a13ef9
purpose: 25 misconceptions
source: src/vibey_tools/skills/plugins/medicine-design-software-development/skills/drugdev-reference/SKILL.md
requires: ["skill-24-what-s-live-verified-august-2026-1fd225292a"]
links: ["skill-26-numbers-9523322014"]
---

## §25. Misconceptions

| Misconception | Correction |
|---|---|
| AI will collapse drug development timelines | ⚠️ **Early-stage yes; clinical attrition unchanged** (§1 → `drugdev-pipeline-targets-and-drug-likeness`, §24.1) |
| The bottleneck is compute | ⚠️ **It's biology and target validation** (§1 → `drugdev-pipeline-targets-and-drug-likeness`) |
| Random train/test split is standard practice | ⚠️ **It leaks badly here. Scaffold or time split** (§7 → `drugdev-representation-cheminformatics-data-quality-and-leakage`) |
| High test R² means the model works | ⚠️ **Check the split, then the noise floor** (§6 → `drugdev-representation-cheminformatics-data-quality-and-leakage`, §7 → `drugdev-representation-cheminformatics-data-quality-and-leakage`) |
| The same molecule has one SMILES | ⚠️ **Canonicalize, or you'll duplicate everything** (§4 → `drugdev-representation-cheminformatics-data-quality-and-leakage`) |
| Lipinski's rules define drug-likeness | ⚠️ **A retrospective observation, not a filter** (§3 → `drugdev-pipeline-targets-and-drug-likeness`) |
| Public bioactivity data is precise | ⚠️ **~1 order of magnitude between labs is common** (§6 → `drugdev-representation-cheminformatics-data-quality-and-leakage`) |
| AlphaFold solved structure for drug design | ⚠️ **Apo-like; docking into it underperforms** (§9 → `drugdev-protein-structure-docking-and-molecular-dynamics`) |
| pLDDT is an accuracy guarantee | ⚠️ **A confidence score; low regions may be disordered** (§9 → `drugdev-protein-structure-docking-and-molecular-dynamics`) |
| Docking scores predict affinity | ⚠️ **Poses reasonable, scoring poor. Triage only** (§10 → `drugdev-protein-structure-docking-and-molecular-dynamics`) |
| Better docking software fixes scoring | ⚠️ **Protein prep matters more than program choice** (§10 → `drugdev-protein-structure-docking-and-molecular-dynamics`) |
| MD tells you what the protein does | ⚠️ **Microseconds vs milliseconds of real biology** (§11 → `drugdev-protein-structure-docking-and-molecular-dynamics`) |
| MM/GBSA is a cheap FEP | ⚠️ **Much less reliable and widely over-trusted** (§12 → `drugdev-protein-structure-docking-and-molecular-dynamics`) |
| Deep learning beats classical QSAR | ⚠️ **RF on ECFP is often competitive. Run it** (§13 → `drugdev-qsar-admet-generative-models-and-validation`, §17 → `drugdev-qsar-admet-generative-models-and-validation`) |
| Similar structure means similar activity | ⚠️ **Activity cliffs, and they're the interesting cases** (§13 → `drugdev-qsar-admet-generative-models-and-validation`) |
| Generating novel molecules is the hard part | ⚠️ **Scoring is. Generators hack the objective** (§15 → `drugdev-qsar-admet-generative-models-and-validation`) |
| Novelty metrics show a generative model works | ⚠️ **Nearly meaningless. Synthesizability matters** (§15 → `drugdev-qsar-admet-generative-models-and-validation`) |
| Benchmark SOTA transfers to practice | ⚠️ **Documented leakage in the standard benchmarks** (§17 → `drugdev-qsar-admet-generative-models-and-validation`) |
| Test-set accuracy is the goal | ⚠️ **Fewer DMTA cycles is the goal** (§16 → `drugdev-qsar-admet-generative-models-and-validation`) |
| Uncertainty estimation is optional | ⚠️ **It's what drives compound selection** (§16 → `drugdev-qsar-admet-generative-models-and-validation`) |
| Validation means a good validation set | ⚠️ **In GxP it means documented qualification** (§22 → `drugdev-pipeline-engineering-compute-and-regulated-software`) |
| Research code can be made GxP later | ⚠️ **Retrofitting traceability is far more expensive** (§22 → `drugdev-pipeline-engineering-compute-and-regulated-software`) |
| A model is validated or not | ⚠️ **Credible for a CONTEXT OF USE, or not** (§24.2) |
| AI-discovered drugs have been approved | ⚠️ **~173 in trials, zero approvals as of 2026** (§24.1) |
| 90% Phase 1 success proves AI works | ⚠️ **Small, likely skewed sample; easier targets** (§24.1) |

---
