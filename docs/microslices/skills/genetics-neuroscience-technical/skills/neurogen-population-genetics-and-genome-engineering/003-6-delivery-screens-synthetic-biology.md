---
id: skill-6-delivery-screens-synthetic-biology-f02b9c4979
purpose: 6 delivery screens synthetic biology
source: src/vibey_tools/skills/plugins/genetics-neuroscience-technical/skills/neurogen-population-genetics-and-genome-engineering/SKILL.md
requires: ["skill-5-genome-engineering-f4a608d778"]
links: []
---

## §6. Delivery, Screens, Synthetic Biology

### 6.1 ⚠️ Delivery is the actual bottleneck

| Vector | Capacity | Notes |
|---|---|---|
| **AAV** | ⚠️ **~4.7 kb** | Non-integrating (mostly), long expression, serotype-dependent tropism. ⚠️ **SpCas9 alone is ~4.2 kb — barely fits, hence dual-vector and compact orthologs** |
| **Lentivirus** | ~8–10 kb | ⚠️ **Integrates — durable but insertional mutagenesis risk** |
| **Adenovirus** | ~30 kb | High immunogenicity |
| **LNP** | large | ⚠️ **Transient, re-dosable, liver-tropic by default. The workhorse for in vivo editing** |
| **Electroporation / RNP** | — | ⚠️ **Ex vivo standard — transient and highly specific** |

**⚠️ Tropism is the constraint that shapes the whole field**: LNPs go to liver
(ApoE-mediated LDLR uptake) unless engineered otherwise. **This is why liver diseases
dominated the in vivo editing pipeline** — not because they were most important, but
because they were reachable. **CNS, muscle and lung remain hard.**

**Immunogenicity**: pre-existing AAV neutralizing antibodies exclude a large fraction of
patients; ⚠️ **and AAV re-dosing is generally not possible.**

### 6.2 Screens
**Pooled CRISPR screens**: library of guides → select or sort → sequence guide abundance →
enrichment/depletion. **Readouts**: viability, reporter, FACS.
**⚠️ Perturb-seq / CROP-seq** couples perturbation with **single-cell transcriptomic
readout**, giving a rich phenotype per perturbation rather than a single number.
**⚠️ Design essentials**: 4–10 guides per gene, non-targeting and safe-harbour controls,
adequate library representation (⚠️ **≥500–1000× coverage; under-representation produces
noise that looks like hits**), and **MAGeCK or similar for analysis.**

### 6.3 Synthetic biology
**Parts** (promoters, RBS, terminators, CDS), **devices**, **systems**. **Standards**:
BioBricks, SBOL. **Circuits**: toggle switch (⚠️ **mutual repression → bistability**),
repressilator (⚠️ **three-node ring → oscillation**), logic gates, **feedback controllers**.
**⚠️ The recurring practical problems**: **burden** (circuits compete with host metabolism),
**evolutionary instability** (⚠️ **a costly circuit is selected against and breaks within
tens of generations**), **context dependence** (a part behaves differently in a new
construct), and **retroactivity** (downstream load changes upstream behaviour).
**Gene drives**: super-Mendelian inheritance via homing; ⚠️ **resistance alleles arise
readily through NHEJ repair at the cut site, which is the central technical obstacle.**
