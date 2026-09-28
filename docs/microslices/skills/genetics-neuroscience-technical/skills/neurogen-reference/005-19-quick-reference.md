---
id: skill-19-quick-reference-ea52cbac08
purpose: 19 quick reference
source: src/vibey_tools/skills/plugins/genetics-neuroscience-technical/skills/neurogen-reference/SKILL.md
requires: ["skill-18-books-379ce7d46a"]
links: ["skill-20-method-d1906e99be"]
---

## §19. Quick Reference

### 19.1 Equations
```
p² + 2pq + q² = 1                       Hardy-Weinberg
h² = V_A/V_P · H² = V_G/V_P             ⚠️ narrow vs broad sense §4.1
D = p_AB − p_A·p_B · D_t = D_0(1−c)^t   linkage disequilibrium decay
q̂ ≈ √(µ/s) recessive · µ/s dominant     mutation-selection balance
PRS_i = Σ_j β_j·G_ij                    polygenic score
λ = √(r_m/r_i) · τ_m = r_m·c_m          cable constants
Δw = η·x·y                              Hebb (⚠️ unstable)
δ = r + γV(s′) − V(s)                   ⚠️ dopamine RPE = TD error §11
I(S;R) = H(R) − H(R|S)                  mutual information
v̂ = Σ r_i·c_i                           population vector
```

### 19.2 Picker
| Need | Tool |
|---|---|
| Knock out a gene | **Cas9 + NHEJ** frameshift (§5.1 → `neurogen-population-genetics-and-genome-engineering`) |
| Precise single-base change | ⚠️ **Base editor (transitions) or prime editor (any)** (§5.1 → `neurogen-population-genetics-and-genome-engineering`) |
| Change expression without editing DNA | **CRISPRi/a (dCas9)** (§5.1 → `neurogen-population-genetics-and-genome-engineering`) |
| Transient knockdown | RNAi or Cas13 (§5.1 → `neurogen-population-genetics-and-genome-engineering`) |
| Edit in post-mitotic tissue | ⚠️ **Base/prime editing — HDR won't work** (§5.1 → `neurogen-population-genetics-and-genome-engineering`) |
| In vivo liver delivery | **LNP** (§6.1 → `neurogen-population-genetics-and-genome-engineering`) |
| Long-term expression, small cargo | **AAV** ⚠️ (4.7 kb) (§6.1 → `neurogen-population-genetics-and-genome-engineering`) |
| Ex vivo cell editing | ⚠️ **RNP electroporation** (§6.1 → `neurogen-population-genetics-and-genome-engineering`) |
| Genome-wide functional screen | Pooled CRISPR; ⚠️ **Perturb-seq for rich readout** (§6.2 → `neurogen-population-genetics-and-genome-engineering`) |
| Millisecond causal circuit test | **Optogenetics** (§13 → `neurogen-circuits-neuromodulation-and-neural-engineering`) |
| Hours-long circuit manipulation | **DREADDs** ⚠️ (CNO caveat) (§13 → `neurogen-circuits-neuromodulation-and-neural-engineering`) |
| Population activity, many neurons | **GCaMP two-photon** or **Neuropixels** (§13 → `neurogen-circuits-neuromodulation-and-neural-engineering`) |
| Single-cell biophysics | **Patch clamp** (§13 → `neurogen-circuits-neuromodulation-and-neural-engineering`) |
| Cell types with spatial position | **MERFISH / spatial transcriptomics** (§13 → `neurogen-circuits-neuromodulation-and-neural-engineering`) |
| Monosynaptic input mapping | **Rabies tracing** (§13 → `neurogen-circuits-neuromodulation-and-neural-engineering`) |
| Check a variant's frequency | ⚠️ **gnomAD, always first** (§18) |

### 19.3 Interpretation checklist
- [ ] Is this "silent" variant actually affecting splicing or translation? (§1.1 → `neurogen-molecular-genetics-and-regulation`)
- [ ] Where is the premature stop relative to the last junction? (NMD) (§1.2 → `neurogen-molecular-genetics-and-regulation`)
- [ ] Assigned the GWAS hit by proximity, or by functional evidence? (§2.1 → `neurogen-molecular-genetics-and-regulation`, §4.3 → `neurogen-population-genetics-and-genome-engineering`)
- [ ] Is penetrance from families (biased) or population data? (§3.2 → `neurogen-molecular-genetics-and-regulation`)
- [ ] Corrected for population stratification? (§4.3 → `neurogen-population-genetics-and-genome-engineering`)
- [ ] Is the PRS being applied outside its discovery ancestry? (§4.3 → `neurogen-population-genetics-and-genome-engineering`)
- [ ] Is heritability being read as an individual property? (§4.1 → `neurogen-population-genetics-and-genome-engineering`)
- [ ] LoF or GoF — does the therapy strategy match? (§3.1 → `neurogen-molecular-genetics-and-regulation`)
- [ ] Is HDR being assumed in post-mitotic tissue? (§5.1 → `neurogen-population-genetics-and-genome-engineering`)
- [ ] Checked on-target structural outcomes, not just off-targets? (§5.1 → `neurogen-population-genetics-and-genome-engineering`)
- [ ] Bystander edits inside the base-editing window? (§5.1 → `neurogen-population-genetics-and-genome-engineering`)
- [ ] Screen library coverage ≥500–1000×? (§6.2 → `neurogen-population-genetics-and-genome-engineering`)
- [ ] Is the optogenetic manipulation physiologically plausible? (§13 → `neurogen-circuits-neuromodulation-and-neural-engineering`)
- [ ] DREADD experiment run with a DREADD-free CNO control? (§13 → `neurogen-circuits-neuromodulation-and-neural-engineering`)
- [ ] Are calcium transients being read as spike counts? (§13 → `neurogen-circuits-neuromodulation-and-neural-engineering`)

---
