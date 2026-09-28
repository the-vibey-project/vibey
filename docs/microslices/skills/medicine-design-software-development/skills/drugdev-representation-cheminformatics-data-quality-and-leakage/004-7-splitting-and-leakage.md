---
id: skill-7-splitting-and-leakage-1b945f38cd
purpose: 7 splitting and leakage
source: src/vibey_tools/skills/plugins/medicine-design-software-development/skills/drugdev-representation-cheminformatics-data-quality-and-leakage/SKILL.md
requires: ["skill-6-data-sources-and-their-quality-3f8edd33f7"]
links: []
---

## §7. ⚠️ Splitting and Leakage

> **⚠️ THE defining methodological failure of ML in this field, and the reason so many
> published models don't work in practice.**
```
⚠️ THE PROBLEM  chemical datasets are ANALOGUE SERIES — dozens of close
   variants around a scaffold, from one medicinal chemistry campaign.
   ⚠️ A RANDOM SPLIT puts near-identical molecules in train AND test,
   so you measure interpolation within a series and call it generalization
⚠️ BETTER SPLITS
   ⚠️ SCAFFOLD SPLIT (Bemis-Murcko) — separates by core structure
   ⚠️ TIME SPLIT — train on what was known before date X, test after.
      ⚠️ The most realistic, because it mirrors actual prospective use
   ⚠️ CLUSTER SPLIT — cluster by similarity, hold out whole clusters
   ⚠️ For targets: hold out whole PROTEIN FAMILIES, not random pairs
⚠️ OTHER LEAKAGE ROUTES
   ⚠️ Duplicate compounds under different SMILES (§4)
   ⚠️ Standardizing or normalizing BEFORE splitting
   ⚠️ Test-set information in feature selection or hyperparameter choice
   ⚠️ Structure-based: the same PROTEIN in train and test with a
      different ligand
```
**⚠️ APPLICABILITY DOMAIN is the corollary and it belongs in the API**: ⚠️ **a model should
report whether a query is within the chemical space it was trained on**, **and a
confident prediction on an out-of-domain molecule is worse than no prediction.**
**⚠️ The honest test**: ⚠️ **can the model predict compounds made AFTER the training data
was assembled?** **Everything else is a proxy.**

---

# PART III — STRUCTURE-BASED METHODS
