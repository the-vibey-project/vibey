---
id: skill-2-gene-regulation-and-epigenetics-03563d1278
purpose: 2 gene regulation and epigenetics
source: src/vibey_tools/skills/plugins/genetics-neuroscience-technical/skills/neurogen-molecular-genetics-and-regulation/SKILL.md
requires: ["skill-1-molecular-genetics-4d4ead2b57"]
links: ["skill-3-mutation-variation-inheritance-01609af8b5"]
---

## §2. Gene Regulation and Epigenetics

### 2.1 Cis-regulation

**Promoters** (proximal), **enhancers** (⚠️ **can act over hundreds of kilobases, in either
orientation, and are frequently not the nearest gene — which is why assigning a GWAS hit
to a gene by proximity is unreliable**), silencers, insulators.

**⚠️ 3D genome organization is the missing piece in most explanations**: **TADs**
(topologically associating domains) bounded by **CTCF/cohesin** loops constrain which
enhancers can reach which promoters. **Disrupting a TAD boundary can cause disease by
letting an enhancer contact the wrong gene** — demonstrated in limb malformations. **The
mechanism is loop extrusion: cohesin extrudes DNA until blocked by convergently-oriented
CTCF sites.**

**Transcription factors** bind short degenerate motifs (~6–12 bp), which occur far too
often by chance — ⚠️ **so specificity comes from combinatorial binding, cooperativity, and
chromatin accessibility, not from the motif alone.**

### 2.2 Chromatin and epigenetic marks

| Mark | Effect |
|---|---|
| **DNA methylation (5mC at CpG)** | ⚠️ **Promoter CpG island methylation → silencing. Gene-body methylation correlates with *expression*** |
| **H3K4me3** | Active promoters |
| **H3K27ac** | ⚠️ **Active enhancers — the standard enhancer mark** |
| **H3K4me1** | Primed/poised enhancers |
| **H3K27me3** | Polycomb repression, ⚠️ **facultative heterochromatin — reversible** |
| **H3K9me3** | Constitutive heterochromatin |
| **H3K36me3** | Gene bodies, transcription elongation |

**⚠️ "Bivalent" domains** (H3K4me3 + H3K27me3) mark developmentally poised genes in stem
cells.

**Imprinting** — parent-of-origin monoallelic expression at ~100–200 loci, via
differentially methylated regions. ⚠️ **Prader-Willi and Angelman syndromes arise from the
same 15q11-13 region depending on parental origin** — the cleanest demonstration that
sequence alone doesn't determine phenotype.

**X-inactivation** via *XIST* lncRNA — ⚠️ **random in humans, producing mosaic females, and
~15% of X genes escape it.**

**⚠️ Transgenerational epigenetic inheritance in mammals is contested.** Most marks are
erased in two reprogramming waves (gametogenesis and post-fertilization). **Claims of
inherited environmental effects are much stronger in plants and *C. elegans* than in
mammals**, and mammalian claims frequently have unexcluded confounds (in-utero exposure
affects three generations at once: mother, fetus, and fetal germline).

### 2.3 Non-coding RNA
**miRNA** (~22 nt, seed match to 3′UTR, translational repression/destabilization —
⚠️ **one miRNA regulates hundreds of targets**), **siRNA**, **piRNA** (transposon defence
in germline), **lncRNA** (⚠️ **thousands annotated, function demonstrated for a small
minority — treat "lncRNA X regulates Y" claims with care**), **circRNA**, **snoRNA**.

---
