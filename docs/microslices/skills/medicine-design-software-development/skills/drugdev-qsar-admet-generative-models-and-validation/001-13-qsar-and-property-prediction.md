---
id: skill-13-qsar-and-property-prediction-bb75f51752
purpose: 13 qsar and property prediction
source: src/vibey_tools/skills/plugins/medicine-design-software-development/skills/drugdev-qsar-admet-generative-models-and-validation/SKILL.md
requires: []
links: ["skill-14-admet-prediction-ac76d820b0"]
---

## §13. QSAR and Property Prediction

**⚠️ Predicting activity or a property from structure — the oldest ML application in the
field, dating to the 1960s.**
```
⚠️ CLASSICAL  descriptors/fingerprints + random forest, SVM or
   gradient boosting. ⚠️ STILL HIGHLY COMPETITIVE, and frequently
   beats deep learning on small datasets — which is most datasets here
⚠️ DEEP  GNNs (message passing on the molecular graph),
   transformers on SMILES, ⚠️ pretrained molecular foundation models
⚠️ MULTITASK  related endpoints trained together often help
```
> **⚠️ GOTCHA — ACTIVITY CLIFFS break the core assumption.** ⚠️ **QSAR assumes similar
> structures have similar activity; activity cliffs are pairs of near-identical molecules
> with order-of-magnitude activity differences, and they are exactly the cases medicinal
> chemists care about.** **⚠️ Models systematically fail on them, and aggregate metrics
> hide this because cliffs are a minority of pairs.**
> **⚠️ Report performance on cliff pairs separately if the model will be used for lead
> optimization.**

**⚠️ Honest expectations**: ⚠️ **on well-populated endpoints with good data, models are
useful triage tools.** **⚠️ They rarely replace an assay, and their value is in ORDERING
what to test next** (§16), **not in producing numbers to quote.**

---
