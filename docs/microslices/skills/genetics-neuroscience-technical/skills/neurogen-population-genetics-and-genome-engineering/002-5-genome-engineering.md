---
id: skill-5-genome-engineering-f4a608d778
purpose: 5 genome engineering
source: src/vibey_tools/skills/plugins/genetics-neuroscience-technical/skills/neurogen-population-genetics-and-genome-engineering/SKILL.md
requires: ["skill-4-population-and-quantitative-genetics-d958f149fe"]
links: ["skill-6-delivery-screens-synthetic-biology-f02b9c4979"]
---

## §5. Genome Engineering

### 5.1 The CRISPR toolbox — mechanisms

**Cas9 (Type II)**: guide RNA (~20 nt spacer) + **PAM** (⚠️ **SpCas9 requires 5′-NGG-3′
immediately 3′ of the protospacer — the PAM is the targeting constraint, and it is why not
every site is editable**) → **blunt double-strand break ~3 bp upstream of PAM.**

**Repair determines outcome** — ⚠️ **this is the crux:**
```
NHEJ    error-prone, indels → ⚠️ frameshift KNOCKOUT. Active in all cell-cycle phases
MMEJ    microhomology-mediated, predictable deletions
HDR     precise KNOCK-IN — ⚠️ requires a donor template AND S/G2 phase,
        so it is inefficient and nearly absent in post-mitotic cells (neurons, muscle)
```
**⚠️ "CRISPR can rewrite any gene" collides with this**: knockout is easy, precise
correction by HDR is hard, and in non-dividing tissue it barely works.

**Cas12a (Cpf1)**: T-rich PAM, **staggered cut**, ⚠️ **processes its own crRNA array —
convenient for multiplexing.** **Cas13**: RNA-targeting, ⚠️ **edits the transcript, so the
effect is transient and the genome is untouched.**

**Base editing (Komor/Gaudelli)** — ⚠️ **no double-strand break:**
```
CBE:  cytosine deaminase + nCas9  → C•G → T•A
ABE:  evolved adenine deaminase + nCas9 → A•T → G•C
```
**⚠️ Editing window is ~4–8 nt within the protospacer**, which creates **bystander
edits** — other identical bases in the window are also changed. **Together CBE and ABE
cover the four transition mutations, but not transversions.**

**Prime editing (Anzalone)**: **nCas9 fused to reverse transcriptase**, guided by a
**pegRNA** that carries both the target and the desired edit as an RT template.
⚠️ **Can install all 12 base substitutions plus small insertions and deletions, without a
double-strand break or a donor template.** **The trade: lower efficiency and a much more
complex reagent to design.**

**CRISPRi/CRISPRa**: **catalytically dead dCas9** fused to KRAB (repress) or VP64/VPR
(activate). ⚠️ **No sequence change at all — a reversible, tunable perturbation, which
makes it the right tool for screens** (§6.2).

**⚠️ Specificity and safety concerns that are real:**
- **Off-target editing** at sites with mismatches. **Mitigate**: high-fidelity variants
  (eSpCas9, HiFi Cas9), truncated guides, RNP delivery (⚠️ **transient exposure — protein
  degrades, unlike plasmid**). **Measure**: GUIDE-seq, CIRCLE-seq, DISCOVER-seq.
- **⚠️ On-target structural consequences are the underrated risk**: large deletions,
  **chromothripsis**, and **loss of heterozygosity** following a double-strand break.
  **This is a major argument for base and prime editing.**
- **p53 activation** — cells with functional p53 respond to DSBs; ⚠️ **selecting for
  successfully edited cells can enrich for p53-deficient ones.**
- **Mosaicism** in embryo editing, and **pre-existing immunity** to Cas9 from
  *S. pyogenes* / *S. aureus* exposure.

### 5.2 Classic and adjacent tools
Restriction enzymes and cloning, **PCR** (⚠️ `2ⁿ` amplification; qPCR `C_t`), **Gibson
assembly**, **Golden Gate**, **ZFNs and TALENs** (⚠️ **protein-DNA recognition — harder to
retarget than CRISPR's RNA guide, which is the entire reason CRISPR won**),
**recombinases** (Cre-lox, Flp-FRT — ⚠️ **the basis of conditional knockouts**),
**RNAi** (transient knockdown, ⚠️ **off-target seed effects are pervasive**),
**transposons** (Sleeping Beauty, PiggyBac).

---
