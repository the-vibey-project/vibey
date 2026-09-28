---
id: skill-19-quick-reference-18fbc49110
purpose: 19 quick reference
source: src/vibey_tools/skills/plugins/biomedical-engineering-technical/skills/biomed-reference/SKILL.md
requires: ["skill-18-books-c523e824dc"]
links: ["skill-20-method-49a09fe19f"]
---

## §19. Quick Reference

### 19.1 Equations
```
PPV = (Sens·Prev)/(Sens·Prev + (1−Spec)(1−Prev))     ⚠️ §4.1
Brier = (1/N)Σ(p_i − y_i)²                            calibration
Dice = 2|A∩B|/(|A|+|B|)                               segmentation
MI(A,B) = H(A)+H(B)−H(A,B)                            multimodal registration
HU = pixel·RescaleSlope + RescaleIntercept            ⚠️ §2.2
E_ion = (RT/zF)ln([out]/[in])                         Nernst
C_m dV/dt = I − ḡ_Na m³h(V−E_Na) − ḡ_K n⁴(V−E_K) − ḡ_L(V−E_L)   Hodgkin-Huxley
v = V_max[S]/(K_m+[S])                                Michaelis-Menten
θ = [L]ⁿ/(K_d+[L]ⁿ)                                   Hill
C(t) = (D/V)e^(−kt) · t½ = ln2/k · CL = kV            PK
C_ss,avg = FD/(CL·τ) · loading = C_target·V/F         PK steady state
E = E_max·Cⁿ/(EC₅₀ⁿ+Cⁿ)                               PD
Q = πΔP r⁴/(8µL)                                      Poiseuille ⚠️ r⁴
Re = ρvD/µ                                            turbulence onset
C dP/dt + P/R = Q(t)                                  2-element Windkessel
A = εcl                                               Beer-Lambert
Z' = 1 − 3(σ_p+σ_n)/|µ_p−µ_n|                        assay quality
h(t|X) = h₀(t)exp(βᵀX)                                Cox
Q = −10 log₁₀ P(error)                                Phred
```

### 19.2 Picker
| Need | Use |
|---|---|
| QRS detection | **Pan–Tompkins** + refractory + searchback (§1.3 → `biomed-signals-and-medical-imaging`) |
| Diagnostic ECG filtering | ⚠️ **0.05–150 Hz, zero-phase** (§1.2 → `biomed-signals-and-medical-imaging`) |
| Remove EEG blinks | **ICA**, or EOG regression (§1.3 → `biomed-signals-and-medical-imaging`) |
| Non-stationary spectral analysis | **Wavelets** (Morlet) or multitaper (§1.3 → `biomed-signals-and-medical-imaging`) |
| Multimodal image registration | ⚠️ **Mutual information + multi-resolution** (§2.4 → `biomed-signals-and-medical-imaging`) |
| Medical segmentation baseline | **nnU-Net** (§2.4 → `biomed-signals-and-medical-imaging`) |
| Segmentation metric that catches bad boundaries | ⚠️ **Hausdorff, not just Dice** (§2.4 → `biomed-signals-and-medical-imaging`) |
| Imbalanced classification metric | **AUPRC**, and calibration (§4.1 → `biomed-clinical-data-ml-and-bioinformatics`–4.2) |
| Fix overconfident network | **Temperature scaling** (§4.2 → `biomed-clinical-data-ml-and-bioinformatics`) |
| Is the model clinically useful | ⚠️ **Decision curve analysis** (§4.2 → `biomed-clinical-data-ml-and-bioinformatics`) |
| Read alignment, short | **BWA-MEM** / Bowtie2 (§5.1 → `biomed-clinical-data-ml-and-bioinformatics`) |
| Read alignment, long | **minimap2** (§5.1 → `biomed-clinical-data-ml-and-bioinformatics`) |
| Germline variants | **GATK HaplotypeCaller** or DeepVariant (§5.2 → `biomed-clinical-data-ml-and-bioinformatics`) |
| Differential expression | ⚠️ **DESeq2/edgeR — negative binomial** (§5.3 → `biomed-clinical-data-ml-and-bioinformatics`) |
| Single-cell clustering | Graph + **Leiden**; ⚠️ UMAP for pictures only (§5.3 → `biomed-clinical-data-ml-and-bioinformatics`) |
| Genome-scale metabolism | **FBA** (§7 → `biomed-structural-systems-biology-and-pharmacology`) |
| Low molecule counts | ⚠️ **Gillespie, not ODEs** (§7 → `biomed-structural-systems-biology-and-pharmacology`) |
| Population PK | **Nonlinear mixed effects**; allometric CL ∝ WT^0.75 (§8 → `biomed-structural-systems-biology-and-pharmacology`) |
| Extrapolate to new population | **PBPK** (§8 → `biomed-structural-systems-biology-and-pharmacology`) |
| Large spiking networks | **Izhikevich** or integrate-and-fire (§9 → `biomed-structural-systems-biology-and-pharmacology`) |
| Repeated measures | ⚠️ **Mixed-effects models** (§15 → `biomed-biomechanics-devices-and-biostatistics`) |
| Many hypotheses | **Benjamini–Hochberg FDR** (§15 → `biomed-biomechanics-devices-and-biostatistics`) |
| Method comparison | ⚠️ **Bland–Altman, not correlation** (§15 → `biomed-biomechanics-devices-and-biostatistics`) |
| Time-to-event with censoring | **Kaplan–Meier + Cox** (§15 → `biomed-biomechanics-devices-and-biostatistics`) |

### 19.3 Debugging checklist
- [ ] Did you apply RescaleSlope/Intercept before treating pixels as HU? (§2.2 → `biomed-signals-and-medical-imaging`)
- [ ] Is laterality derived from ImageOrientationPatient, not display? (§2.2 → `biomed-signals-and-medical-imaging`)
- [ ] Slice spacing computed from positions, not SliceThickness? (§2.2 → `biomed-signals-and-medical-imaging`)
- [ ] MRI intensities normalized before cross-site modelling? (§2.1 → `biomed-signals-and-medical-imaging`)
- [ ] ECG filter band appropriate to the claim (diagnostic vs monitoring)? (§1.2 → `biomed-signals-and-medical-imaging`)
- [ ] Zero-phase filtering where intervals are measured? (§1.2 → `biomed-signals-and-medical-imaging`)
- [ ] Split by patient, not by sample? (§4.4 → `biomed-clinical-data-ml-and-bioinformatics`)
- [ ] Any feature downstream of clinical suspicion? (§4.3 → `biomed-clinical-data-ml-and-bioinformatics`)
- [ ] Missingness modelled rather than naively imputed? (§4.3 → `biomed-clinical-data-ml-and-bioinformatics`)
- [ ] PPV computed at the *deployment* prevalence? (§4.1 → `biomed-clinical-data-ml-and-bioinformatics`)
- [ ] Calibration checked, not just discrimination? (§4.2 → `biomed-clinical-data-ml-and-bioinformatics`)
- [ ] Units stored with values; UCUM? (§3 → `biomed-clinical-data-ml-and-bioinformatics`)
- [ ] Negation handled in any text processing? (§3 → `biomed-clinical-data-ml-and-bioinformatics`)
- [ ] Read depth adequate for germline vs somatic? (§5.2 → `biomed-clinical-data-ml-and-bioinformatics`)
- [ ] Normalization method valid for across-sample comparison? (§5.3 → `biomed-clinical-data-ml-and-bioinformatics`)
- [ ] Both pLDDT and PAE checked on predicted structures? (§6 → `biomed-structural-systems-biology-and-pharmacology`)
- [ ] Proportional hazards assumption tested? (§15 → `biomed-biomechanics-devices-and-biostatistics`)
- [ ] Clustering/repeated measures accounted for in the model? (§15 → `biomed-biomechanics-devices-and-biostatistics`)

---
