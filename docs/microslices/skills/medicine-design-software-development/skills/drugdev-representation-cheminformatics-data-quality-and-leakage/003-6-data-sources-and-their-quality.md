---
id: skill-6-data-sources-and-their-quality-3f8edd33f7
purpose: 6 data sources and their quality
source: src/vibey_tools/skills/plugins/medicine-design-software-development/skills/drugdev-representation-cheminformatics-data-quality-and-leakage/SKILL.md
requires: ["skill-5-cheminformatics-toolkits-8954017c08"]
links: ["skill-7-splitting-and-leakage-1b945f38cd"]
---

## §6. ⚠️ Data Sources and Their Quality

```
⚠️ ChEMBL   curated bioactivity from literature. ⚠️ THE main public
   resource, and ⚠️ its heterogeneity is the problem: assays differ
PubChem     enormous, ⚠️ much less curated
BindingDB   binding affinities · ⚠️ PDB / PDBbind for structures
DrugBank · ZINC / Enamine REAL (⚠️ purchasable and enumerated —
   billions of compounds) · ⚠️ Open Reaction Database · TDC benchmarks
⚠️ PROPRIETARY  internal pharma data is usually better-controlled and
   is why in-house models can outperform published ones
```
> **⚠️ GOTCHA — public bioactivity data is far noisier than its precision suggests.**
> ⚠️ **The same compound-target pair measured in different labs commonly differs by
> around an order of magnitude, and published experimental error on pIC50 is often
> estimated near 0.5 log units.** **⚠️ That sets a CEILING on achievable model accuracy
> that no architecture can exceed** — **a model reporting RMSE well below the
> experimental noise floor is fitting the noise, the assay, or the split** (§7).
> **⚠️ Also beware: activity data is heavily biased toward what was measured, censored
> values ("> 10 μM") are frequently mishandled, and ⚠️ inactives are massively
> under-reported because negative results aren't published.**

---
