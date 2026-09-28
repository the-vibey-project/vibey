---
id: skill-17-benchmarks-91610af8a3
purpose: 17 benchmarks
source: src/vibey_tools/skills/plugins/medicine-design-software-development/skills/drugdev-qsar-admet-generative-models-and-validation/SKILL.md
requires: ["skill-16-active-learning-and-the-dmta-loop-fe0fe4522c"]
links: ["skill-18-validation-that-means-something-690a6577ef"]
---

## §17. ⚠️ Benchmarks

**⚠️ Common ones**: **MoleculeNet, Therapeutics Data Commons (TDC), DUD-E and LIT-PCBA
(virtual screening), CASF and PDBbind (scoring), GuacaMol and MOSES (generative), and
polaris-style curated benchmarks.**
> **⚠️ GOTCHA — most published benchmark improvements do not transfer, and there are
> documented structural reasons.** ⚠️ **MoleculeNet's random splits are known to inflate
> results (§7 → `drugdev-representation-cheminformatics-data-quality-and-leakage`); DUD-E's decoys are separable from actives by trivial properties, so models
> learn the decoy generation procedure; PDBbind has train-test protein overlap; and
> generative benchmarks reward distributional metrics that don't correspond to usefulness.**
> **⚠️ Independent reanalyses have repeatedly found that simple baselines — random forest
> on ECFP fingerprints — match or beat elaborate architectures once splits are fixed.**
> **⚠️ Always run that baseline. If your model doesn't beat it, you have learned something
> important.**

---
