---
id: skill-2-targets-and-modalities-3dbb671865
purpose: 2 targets and modalities
source: src/vibey_tools/skills/plugins/medicine-design-software-development/skills/drugdev-pipeline-targets-and-drug-likeness/SKILL.md
requires: ["skill-1-the-pipeline-and-where-software-helps-9cd9a67cac"]
links: ["skill-3-what-makes-a-molecule-a-drug-b0c816b08e"]
---

## §2. Targets and Modalities

**⚠️ Targets**: **enzymes (kinases, proteases), GPCRs, ion channels, nuclear receptors,
protein-protein interfaces (⚠️ historically "undruggable" — flat, large surfaces with no
pocket).**
**⚠️ Target validation is the highest-value and least computational step**: ⚠️ **genetic
evidence that modulating the target changes the disease is the strongest predictor of
clinical success, and human genetics-supported targets have a substantially better track
record.**
**⚠️ Modalities and their very different computational problems:**
```
SMALL MOLECULES  ⚠️ the classic cheminformatics domain (most of this doc)
BIOLOGICS  ⚠️ antibodies — sequence and structure problems, not SMILES
PROTACs / molecular glues  ⚠️ TERNARY complexes; conventional
   affinity-driven design does not apply
PEPTIDES · OLIGONUCLEOTIDES (ASO, siRNA) · ⚠️ mRNA and vaccines ·
CELL AND GENE THERAPY
```
**⚠️ Do not assume small-molecule tooling transfers** — ⚠️ **RDKit and docking are largely
irrelevant to antibody engineering, which is a sequence/structure problem with its own
stack.**

---
