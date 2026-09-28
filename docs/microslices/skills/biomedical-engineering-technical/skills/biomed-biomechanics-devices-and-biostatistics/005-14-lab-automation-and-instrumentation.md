---
id: skill-14-lab-automation-and-instrumentation-841743ba70
purpose: 14 lab automation and instrumentation
source: src/vibey_tools/skills/plugins/biomedical-engineering-technical/skills/biomed-biomechanics-devices-and-biostatistics/SKILL.md
requires: ["skill-13-neural-interfaces-and-prosthetics-86bf595f85"]
links: ["skill-15-biostatistics-afbf74cfb6"]
---

## §14. Lab Automation and Instrumentation

**Liquid handling** — ⚠️ **the practical constraints are viscosity, surface tension,
evaporation from edge wells, and carryover.** Acoustic dispensing (Echo) avoids tips
entirely and reaches nanolitre volumes.

**Plate formats**: 96 / 384 / 1536, and ⚠️ **edge effects are real — evaporation makes
perimeter wells systematically different. Randomize plate layout, or exclude edges.**

**Detection**: absorbance (Beer–Lambert `A = εcl`), fluorescence (⚠️ **sensitive but
subject to photobleaching and inner-filter effects**), luminescence, flow cytometry
(⚠️ **compensation for spectral overlap is mandatory and routinely done badly**),
mass spectrometry, and **qPCR** (`C_t` values; efficiency-corrected ΔΔC_t).

**Sequencing chemistries**: **Illumina** (sequencing-by-synthesis, short, ⚠️ **very high
accuracy Q30+**), **Oxford Nanopore** (⚠️ **long reads, real-time, higher raw error but
excellent for structural variants and assembly**), **PacBio HiFi** (long *and* accurate via
circular consensus).

**Assay quality metrics**: **Z' factor** `= 1 − 3(σ_p + σ_n)/|µ_p − µ_n|` — ⚠️ **>0.5 is a
usable screening assay; this single number is how high-throughput screens are validated.**
**CV**, **LOD/LOQ**, and dynamic range.

**⚠️ Standards worth using**: **SiLA 2** and **OPC-UA** for instrument integration,
**AnIML/ADF** for data. **The recurring practical problem is vendor-proprietary formats
and drivers**, which is why lab data integration is disproportionately painful.

---
