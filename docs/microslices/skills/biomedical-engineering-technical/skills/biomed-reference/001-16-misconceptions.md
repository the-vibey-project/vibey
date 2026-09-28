---
id: skill-16-misconceptions-f30e0c365e
purpose: 16 misconceptions
source: src/vibey_tools/skills/plugins/biomedical-engineering-technical/skills/biomed-reference/SKILL.md
requires: []
links: ["skill-17-numbers-035eaa586b"]
---

## §16. Misconceptions

| Claim | Reality |
|---|---|
| "95% sensitivity and specificity means a positive is probably real" | ⚠️ **At 1% prevalence, PPV is 16%** (§4.1 → `biomed-clinical-data-ml-and-bioinformatics`) |
| "High AUROC means the model is clinically useful" | ⚠️ **AUROC is prevalence-independent and says nothing about calibration or net benefit** (§4.2 → `biomed-clinical-data-ml-and-bioinformatics`) |
| "Accuracy is a reasonable metric" | ⚠️ **99% by always predicting the majority class** (§4.1 → `biomed-clinical-data-ml-and-bioinformatics`) |
| "The model generalizes — we cross-validated" | ⚠️ **Internal CV is rung one of five** (§4.4 → `biomed-clinical-data-ml-and-bioinformatics`) |
| "We split randomly, so it's fair" | ⚠️ **Split by patient. Slices from one patient leak** (§4.4 → `biomed-clinical-data-ml-and-bioinformatics`) |
| "MRI intensities are comparable across scans" | ⚠️ **They have no absolute meaning. CT's Hounsfield units do** (§2.1 → `biomed-signals-and-medical-imaging`) |
| "The pixel values are Hounsfield units" | ⚠️ **Not until you apply RescaleSlope/Intercept** (§2.2 → `biomed-signals-and-medical-imaging`) |
| "Dice 0.9 means the segmentation is good" | ⚠️ **Dice is insensitive to small catastrophic boundary errors. Check Hausdorff** (§2.4 → `biomed-signals-and-medical-imaging`) |
| "UMAP shows the cell types are far apart" | ⚠️ **UMAP distances and cluster sizes are artifacts** (§5.3 → `biomed-clinical-data-ml-and-bioinformatics`) |
| "AlphaFold solved protein structure" | ⚠️ **Single static conformations. Check pLDDT *and* PAE** (§6 → `biomed-structural-systems-biology-and-pharmacology`) |
| "Half-life determines dosing" | ⚠️ **Clearance is the physiological parameter; t½ is derived** (§8 → `biomed-structural-systems-biology-and-pharmacology`) |
| "Double the dose, double the concentration" | ⚠️ **Not with saturable elimination — phenytoin, ethanol** (§8 → `biomed-structural-systems-biology-and-pharmacology`) |
| "Volume of distribution is a real volume" | ⚠️ **Apparent; can exceed total body water** (§8 → `biomed-structural-systems-biology-and-pharmacology`) |
| "A notch filter cleans up the ECG" | ⚠️ **60 Hz is inside the diagnostic band; it distorts the QRS** (§1.2 → `biomed-signals-and-medical-imaging`) |
| "Any ECG filter setting is fine" | ⚠️ **0.5–40 Hz monitoring settings invalidate ST analysis** (§1.2 → `biomed-signals-and-medical-imaging`) |
| "Missing lab values should be imputed" | ⚠️ **Missingness is a clinical decision and is informative** (§4.3 → `biomed-clinical-data-ml-and-bioinformatics`) |
| "The implant should be as strong as possible" | ⚠️ **Stiffness mismatch causes stress shielding and resorption** (§10 → `biomed-biomechanics-devices-and-biostatistics`, §11 → `biomed-biomechanics-devices-and-biostatistics`) |
| "We can grow a solid organ" | ⚠️ **~150–200 µm oxygen diffusion limit. Vascularization is unsolved** (§12 → `biomed-biomechanics-devices-and-biostatistics`) |
| "Spike sorting is required for BCI" | ⚠️ **Threshold crossings work well for many decoders** (§13.2 → `biomed-biomechanics-devices-and-biostatistics`) |
| "The BCI electrode will last" | ⚠️ **Glial encapsulation degrades signal over months** (§13.1 → `biomed-biomechanics-devices-and-biostatistics`) |
| "r = 0.99 means the two methods agree" | ⚠️ **Use Bland–Altman. One can read double the other** (§15 → `biomed-biomechanics-devices-and-biostatistics`) |
| "Repeated measures can be pooled" | ⚠️ **Inflates N and manufactures significance. Mixed models** (§15 → `biomed-biomechanics-devices-and-biostatistics`) |
| "Blood is a Newtonian fluid" | Shear-thinning; Fåhræus–Lindqvist in small vessels (§9 → `biomed-structural-systems-biology-and-pharmacology`) |
| "TPM lets me compare samples" | ⚠️ **Within-sample only. Use median-of-ratios or TMM across** (§5.3 → `biomed-clinical-data-ml-and-bioinformatics`) |

---
