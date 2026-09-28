---
id: skill-16-active-learning-and-the-dmta-loop-fe0fe4522c
purpose: 16 active learning and the dmta loop
source: src/vibey_tools/skills/plugins/medicine-design-software-development/skills/drugdev-qsar-admet-generative-models-and-validation/SKILL.md
requires: ["skill-15-generative-models-52158818bf"]
links: ["skill-17-benchmarks-91610af8a3"]
---

## §16. Active Learning and the DMTA Loop

**⚠️ The framing that makes ML in this domain make sense** (§1 → `drugdev-pipeline-targets-and-drug-likeness`): ⚠️ **you are not building a
model to be accurate; you are building a model to CHOOSE WHAT TO TEST NEXT.**
```
⚠️ The loop: model → select compounds → SYNTHESIZE AND ASSAY →
   retrain → repeat
⚠️ ACQUISITION  exploit (best predicted) vs explore (most uncertain) vs
   diverse batch selection. ⚠️ Batch selection matters because you make
   compounds in batches, not one at a time
⚠️ THEREFORE UNCERTAINTY QUANTIFICATION IS A FIRST-CLASS REQUIREMENT,
   not a nice-to-have. ⚠️ Ensembles, conformal prediction, Gaussian
   processes on fingerprints
⚠️ THE METRIC THAT MATTERS  ⚠️ how many DMTA cycles to reach the target
   profile — not test-set R²
```
**⚠️ Self-driving labs and closed-loop automation** connect this to robotic synthesis and
assay — ⚠️ **and the real bottleneck becomes assay throughput and reliability, not
prediction.**

---
