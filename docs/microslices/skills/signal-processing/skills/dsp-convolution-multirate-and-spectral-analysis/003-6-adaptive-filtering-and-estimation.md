---
id: skill-6-adaptive-filtering-and-estimation-ba3770d0cf
purpose: 6 adaptive filtering and estimation
source: src/vibey_tools/skills/plugins/signal-processing/skills/dsp-convolution-multirate-and-spectral-analysis/SKILL.md
requires: ["skill-5-multirate-098a663cdc"]
links: ["skill-7-spectral-analysis-and-time-frequency-abeb180311"]
---

## §6. Adaptive Filtering and Estimation

**[DURABLE] When the filter must learn its own coefficients.**

**LMS** — gradient descent on the error. ⚠️ **Simple, cheap, robust, and the workhorse.
Its convergence depends on the step size and on the input's eigenvalue spread**; NLMS
normalizes for input power and is what you should actually use. **RLS** — much faster
convergence, O(n²) per sample, ⚠️ **and numerically fragile.** **Frequency-domain adaptive
filters** for long responses.

**Applications, and the pattern is the same in all of them**: **echo cancellation**
(⚠️ **model the echo path, subtract the prediction** — §8.3 → `dsp-audio-rf-and-images`), **noise cancellation** with a
reference mic, **channel equalization** (§9 → `dsp-audio-rf-and-images`), **system identification**, and
**line enhancement**.

**Kalman filtering** is the optimal recursive estimator for linear-Gaussian systems —
⚠️ **and the crossover point where signal processing becomes state estimation.** EKF, UKF,
and particle filters for nonlinear cases. **Wiener filtering** is the optimal
*non-adaptive* linear filter given known spectra, and it remains the theoretical baseline
that §8 → `dsp-audio-rf-and-images`'s learned enhancers are measured against.

**⚠️ The recurring practical failures**: **step size too large diverges, too small never
converges**; **double-talk** in echo cancellation (⚠️ **when both ends speak, adaptation
must freeze or the filter destroys itself** — a double-talk detector is mandatory);
**insufficient excitation** means the filter can't identify what it can't hear; and
**non-stationarity** breaks the assumptions everything rests on.

---
