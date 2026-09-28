---
id: skill-10-docking-e5b9961981
purpose: 10 docking
source: src/vibey_tools/skills/plugins/medicine-design-software-development/skills/drugdev-protein-structure-docking-and-molecular-dynamics/SKILL.md
requires: ["skill-9-structure-prediction-235c3dc197"]
links: ["skill-11-molecular-dynamics-705ed12bb0"]
---

## §10. ⚠️ Docking

**⚠️ Predicts a binding POSE and scores it. Understand what each half can do.**
```
⚠️ POSE PREDICTION  ⚠️ reasonably good — often gets a near-native pose
   in the top ranks for well-behaved systems
⚠️ SCORING / AFFINITY RANKING  ⚠️ POOR. ⚠️ Docking scores correlate
   weakly with measured affinity, and this has been true for decades
   despite continuous effort
⚠️ THEREFORE  use docking to ENRICH and TRIAGE, never to rank a
   final series or to claim a predicted potency
```
**⚠️ Programs**: **AutoDock Vina (free, widely used), Glide, GOLD, rDock, DiffDock and
other ML pose predictors** (⚠️ **and note ML docking methods have been criticized for
benchmark leakage — the same protein appearing in train and test** — §7 → `drugdev-representation-cheminformatics-data-quality-and-leakage`).
**⚠️ Practical determinants of whether docking is useful at all**: ⚠️ **protein preparation
(protonation, tautomers, missing atoms) matters more than the choice of program; ⚠️ the
ligand's protonation state at pH 7.4; ⚠️ receptor flexibility (ensemble docking as a
partial answer); and ⚠️ a well-chosen box.**
**⚠️ Virtual screening realities**: ⚠️ **enrichment factors matter more than hit rate;
decoy selection biases benchmarks badly (DUD-E has known artefacts that let models learn
decoy properties rather than binding); and ⚠️ ultra-large library screening of billions of
compounds is now feasible and shifts the bottleneck to synthesis and assay throughput.**

---
