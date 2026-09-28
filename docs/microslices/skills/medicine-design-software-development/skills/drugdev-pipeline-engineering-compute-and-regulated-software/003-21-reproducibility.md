---
id: skill-21-reproducibility-41703d4009
purpose: 21 reproducibility
source: src/vibey_tools/skills/plugins/medicine-design-software-development/skills/drugdev-pipeline-engineering-compute-and-regulated-software/SKILL.md
requires: ["skill-20-compute-9980680245"]
links: ["skill-22-gxp-validation-and-the-regulated-context-6768e4834f"]
---

## §21. Reproducibility

**⚠️ Higher stakes than usual, because results may support regulatory decisions** (§22).
**⚠️ The specific hazards here**: ⚠️ **RDKit version changes altering descriptors (§5 → `drugdev-representation-cheminformatics-data-quality-and-leakage`);
force field version differences (§11 → `drugdev-protein-structure-docking-and-molecular-dynamics`); MD being non-deterministic by nature (⚠️ so
reproducibility means the ENSEMBLE and the seed and the exact configuration, not identical
trajectories); GPU non-determinism in deep learning; and ⚠️ random seeds in splitting,
which is where §7 → `drugdev-representation-cheminformatics-data-quality-and-leakage`'s leakage often hides.**
**⚠️ The practices**: **containers with pinned versions, environment lock files, ⚠️ data
versioning (DVC or equivalent), experiment tracking, and ⚠️ recording the exact input
structures and standardization pipeline used** — **not just "from ChEMBL."**

---
