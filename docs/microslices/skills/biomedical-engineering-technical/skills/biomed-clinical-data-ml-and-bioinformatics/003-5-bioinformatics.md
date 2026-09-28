---
id: skill-5-bioinformatics-5e53cd6565
purpose: 5 bioinformatics
source: src/vibey_tools/skills/plugins/biomedical-engineering-technical/skills/biomed-clinical-data-ml-and-bioinformatics/SKILL.md
requires: ["skill-4-clinical-ml-technicals-ae0529a008"]
links: []
---

## §5. Bioinformatics

### 5.1 Sequence alignment

**Pairwise, dynamic programming**: **Needleman–Wunsch** (global, `O(mn)`),
**Smith–Waterman** (local — ⚠️ **the difference is a zero floor in the recurrence and
traceback from the maximum cell**), with **affine gap penalties** (`gap_open` +
`k·gap_extend`) via Gotoh's three-matrix formulation, because a single long indel is
biologically far more likely than many separate ones.

**Substitution matrices**: **BLOSUM62** (protein, from blocks of aligned segments —
⚠️ **the default for most protein searches**), PAM series, and simple match/mismatch for
DNA.

**Heuristic search**: **BLAST** — seed with exact word matches, extend, evaluate.
⚠️ **E-value = expected number of hits this good by chance in a database this size**, so
**it depends on database size** — the same alignment gets a different E-value in a bigger
database.

**Read alignment at scale**: **BWA-MEM**, **Bowtie2**, **minimap2** (⚠️ **long reads**) —
all built on the **FM-index / Burrows-Wheeler transform**, giving `O(m)` substring search
in a compressed index. **This data structure is why resequencing became tractable.**

### 5.2 Variant calling

```
FASTQ → QC/trim → align (BAM) → mark duplicates → base recalibration
      → call variants (VCF) → filter → annotate → interpret
```
**Callers**: GATK HaplotypeCaller (⚠️ **local reassembly rather than pure pileup**),
DeepVariant (CNN over pileup images), FreeBayes, Strelka2. **Structural variants**:
Manta, DELLY, and long reads, which are far better at them.

**⚠️ The technical difficulties:**
- **Repetitive regions and segmental duplications** — ⚠️ **mapping quality collapses; reads
  map ambiguously and variants there are unreliable.**
- **Indel realignment** around true indels, which otherwise generate false SNVs.
- **Strand bias, allele balance** — a heterozygote should be ~50%; deviation signals
  artifact. **Somatic calling has no such expectation** because of tumour purity and
  subclonality.
- **⚠️ Coverage depth requirements differ enormously**: ~30× for germline SNVs, **but
  100–1000× for somatic variants at low allele fraction.**
- **Reference bias** — reads carrying the alternate allele map slightly worse.
  ⚠️ **Pangenome graph references (e.g. GRCh38 → draft human pangenome) address this** and
  are the direction of travel.

**Formats**: FASTQ (⚠️ **Phred quality `Q = −10 log₁₀ P(error)`; Q30 = 1 in 1000**),
SAM/BAM/CRAM, VCF, BED, GFF/GTF.

### 5.3 Expression and single-cell
**Bulk RNA-seq**: quantify (Salmon/kallisto — ⚠️ **pseudoalignment, dramatically faster**),
then differential expression with **DESeq2** or **edgeR** — ⚠️ **which model counts as
negative binomial, because RNA-seq is overdispersed relative to Poisson.**
**⚠️ Normalization matters more than the test**: TPM within-sample, but **median-of-ratios
or TMM across samples** — RPKM/FPKM are not comparable between samples.

**Single-cell**: QC (⚠️ **MAD-based filtering on counts, genes, and mitochondrial
fraction**) → normalize → HVG selection → PCA → neighbourhood graph → **Leiden
clustering** → UMAP.
> **⚠️ GOTCHA — UMAP and t-SNE distances are not meaningful.** Cluster *sizes*,
> inter-cluster *distances*, and apparent density are artifacts of the embedding.
> **Use them to visualize, never to quantify.** Conclusions must come from the graph or
> the expression, not the picture.

**Batch effects** are pervasive: Harmony, scVI, Combat. ⚠️ **Over-correction merges real
biology; under-correction leaves batch as the dominant axis. There is no automatic
answer.**
