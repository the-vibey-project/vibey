---
id: skill-4-population-and-quantitative-genetics-d958f149fe
purpose: 4 population and quantitative genetics
source: src/vibey_tools/skills/plugins/genetics-neuroscience-technical/skills/neurogen-population-genetics-and-genome-engineering/SKILL.md
requires: []
links: ["skill-5-genome-engineering-f4a608d778"]
---

## §4. Population and Quantitative Genetics

### 4.1 ⚠️ Heritability — the most misused number in biology

**Hardy–Weinberg**: `p² + 2pq + q² = 1` under random mating, no selection/drift/migration/
mutation. ⚠️ **Deviation is usually a genotyping artifact, and HWE testing is a standard
QC filter before it is ever a biological finding.**

**Variance decomposition**: `V_P = V_G + V_E + V_GxE`, with `V_G = V_A + V_D + V_I`.
```
Broad-sense  H² = V_G / V_P
Narrow-sense h² = V_A / V_P     ⚠️ additive only — this is what responds to selection
```

> **⚠️ GOTCHA — what heritability does NOT mean.**
> - **It is a property of a population in an environment**, not of a trait or a person.
>   ⚠️ **"h² = 0.8" says nothing about any individual.**
> - **It says nothing about malleability.** ⚠️ **Height is highly heritable and rose
>   dramatically with nutrition. Phenylketonuria is fully genetic and fully treated by
>   diet.**
> - **⚠️ High h² requires low environmental variance.** In a uniform environment,
>   heritability rises mechanically — because the denominator shrank, not because genes
>   matter more.
> - **⚠️ It says nothing about between-group differences.** Within-group heritability is
>   mathematically compatible with a purely environmental between-group gap — Lewontin's
>   seed-lot argument.

### 4.2 Evolutionary forces
**Selection**: `Δp ≈ spq/w̄` for weak selection. **Drift**: variance `pq/2N_e`, and
⚠️ **fixation probability of a new neutral allele is 1/2N — small populations lose
variation fast.** **Effective population size N_e** is usually much smaller than census
size. **Mutation-selection balance**: `q̂ ≈ √(µ/s)` for recessives, `q̂ ≈ µ/s` for
dominants.

**Linkage disequilibrium**: `D = p_AB − p_A p_B`, normalized as `D′` and `r²`.
⚠️ **LD decays with recombination and time: `D_t = D_0(1−c)^t`.** **This is the entire
basis of GWAS** — you genotype a tag SNP and detect an association driven by an
ungenotyped causal variant in LD with it, ⚠️ **which is why the lead SNP is usually not
causal.**

### 4.3 GWAS and polygenic scores

**Model**: `y = Xβ + ε` per variant, with **genome-wide significance at p < 5 × 10⁻⁸**
(⚠️ **Bonferroni for ~1 million independent tests**).

**⚠️ The technical requirements that make or break a GWAS:**
- **Population stratification** — ancestry correlates with both genotype and phenotype,
  producing spurious associations. **Correct with principal components or linear mixed
  models.** ⚠️ **Uncorrected stratification is the classic GWAS failure.**
- **Fine-mapping** — the lead SNP is in LD with dozens of others (§4.2).
  **Credible sets, not single variants.**
- **⚠️ Variant-to-gene assignment is genuinely hard.** Most hits are non-coding and
  regulatory; **the nearest gene is often wrong** (§2.1 → `neurogen-molecular-genetics-and-regulation`). Use eQTL colocalization,
  chromatin contact data, or functional follow-up.

**Polygenic scores**: `PRS_i = Σ_j β_j · G_ij`.
> **⚠️ GOTCHA — PRS portability across ancestries is poor, and the reason is structural.**
> Predictive accuracy **drops substantially in populations distant from the discovery
> cohort**, because LD patterns, allele frequencies, and effect sizes all differ. **Since
> discovery cohorts have been overwhelmingly European-ancestry, PRS work worst where they
> are most needed.** This is a property of the method plus the sampling, not a fixable
> analysis choice.

**Missing heritability** — GWAS-explained variance long fell short of twin-study `h²`.
⚠️ **Largely resolved by**: many variants of tiny effect below significance thresholds
(SNP-heritability from GREML/LDSC captures much more), rare variants not on arrays, and
⚠️ **upward bias in twin-study estimates from shared-environment and assortative-mating
assumptions.**

---
