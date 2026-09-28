---
id: skill-3-what-makes-a-molecule-a-drug-b0c816b08e
purpose: 3 what makes a molecule a drug
source: src/vibey_tools/skills/plugins/medicine-design-software-development/skills/drugdev-pipeline-targets-and-drug-likeness/SKILL.md
requires: ["skill-2-targets-and-modalities-3dbb671865"]
links: []
---

## §3. ⚠️ What Makes a Molecule a Drug

**⚠️ Potency is the easy part. Almost everything hard is about what the body does to the
molecule.**
```
⚠️ POTENCY  IC50, Ki, Kd, EC50 — ⚠️ note these are assay-dependent and
   NOT directly comparable across labs or formats (§6)
⚠️ SELECTIVITY  ⚠️ hitting the target and NOT the 500 similar proteins
⚠️ ADME  Absorption, Distribution, Metabolism, Excretion
⚠️ TOXICITY  ⚠️ hERG (cardiac), hepatotoxicity, genotoxicity, reactive
   metabolites
⚠️ DEVELOPABILITY  solubility, stability, synthesizability, cost,
   crystallinity, formulation
⚠️ LIGAND EFFICIENCY  LE = ΔG/heavy atoms; LLE = pIC50 − logP
   ⚠️ These exist because raw potency can be bought with lipophilicity,
   which then wrecks everything else
```
> **⚠️ GOTCHA — Lipinski's Rule of Five is widely misused as a filter, and Lipinski said
> otherwise.** ⚠️ **It was a retrospective ORAL BIOAVAILABILITY observation, explicitly not
> a design rule, and it does not apply to natural products, actively transported
> compounds, antibiotics, or beyond-Rule-of-5 space where important drugs live.**
> **⚠️ Hard-filtering a virtual library on Ro5 discards real chemistry.** **⚠️ Use it as a
> soft flag; the related PAINS filters deserve the same caution — they flag frequent
> hitters, and treating them as a validated exclusion list has been criticized in the
> literature.**

---

# PART II — REPRESENTATION AND DATA
