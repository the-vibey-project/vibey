---
id: skill-9-neural-coding-dfa2e30272
purpose: 9 neural coding
source: src/vibey_tools/skills/plugins/genetics-neuroscience-technical/skills/neurogen-neuron-biophysics-plasticity-and-coding/SKILL.md
requires: ["skill-8-plasticity-f49ae19a33"]
links: []
---

## §9. Neural Coding

**Rate coding** — information in firing frequency. Simple, robust, ⚠️ **and slow: estimating
a rate takes time.**
**Temporal coding** — spike timing carries information. ⚠️ **Demonstrated in auditory
localization (microsecond interaural timing) and in olfaction; contested elsewhere.**
**Population coding** — ⚠️ **the modern default**. Information is distributed; individual
neurons are noisy and ambiguous.

**Tuning curves and the population vector**: `v̂ = Σ_i r_i · c_i` — the classic result from
motor cortex, and the basis of early BCI decoders (see a biomedical-engineering
reference §13).

**⚠️ Noise correlations matter and are counterintuitive**: correlated variability between
neurons can either help or hurt population coding depending on whether the correlation
aligns with the signal direction. **Averaging over more neurons does not reduce noise if
the noise is shared.**

**Information theory**: `I(S;R) = H(R) − H(R|S)`. ⚠️ **Estimating mutual information from
limited spike data is severely biased upward; bias-correction is mandatory.**

**Efficient coding** (Barlow) — sensory systems decorrelate and match their dynamic range
to input statistics. ⚠️ **Predicts centre-surround receptive fields and adaptation from
first principles**, and it works.
**Predictive coding** — cortex propagates prediction *error*, not raw signal.
⚠️ **Influential and genuinely contested; the anatomical evidence for the required
error-unit populations is debated.**
**Sparse coding** — few active units, overcomplete basis; ⚠️ **learning sparse codes on
natural images reproduces V1 simple-cell receptive fields.**

**⚠️ Dimensionality**: population activity typically occupies a **low-dimensional manifold**
far smaller than the number of neurons. **Neural trajectories, fixed points and line
attractors are the current working vocabulary for cortical computation.**
