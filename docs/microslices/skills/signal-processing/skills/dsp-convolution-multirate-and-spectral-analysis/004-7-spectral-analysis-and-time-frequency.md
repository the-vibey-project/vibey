---
id: skill-7-spectral-analysis-and-time-frequency-abeb180311
purpose: 7 spectral analysis and time frequency
source: src/vibey_tools/skills/plugins/signal-processing/skills/dsp-convolution-multirate-and-spectral-analysis/SKILL.md
requires: ["skill-6-adaptive-filtering-and-estimation-ba3770d0cf"]
links: []
---

## §7. Spectral Analysis and Time-Frequency

**7.1 Estimating a spectrum properly.** ⚠️ **A single FFT magnitude is a terrible spectral
estimator** — its variance doesn't decrease with more data. **Welch's method** (average
periodograms over overlapping windows) trades resolution for variance reduction and is the
correct default. **Bartlett** is the non-overlapping version; **multitaper** (Thomson)
uses orthogonal windows and is the best general-purpose estimator when you can afford it.

**7.2 Time-frequency.** **STFT/spectrogram** — ⚠️ **fixed resolution at every frequency,
which is its central limitation.** **Wavelets** and **constant-Q transforms** give
finer time resolution at high frequencies and finer frequency resolution at low —
⚠️ **which matches both human hearing and most physical signals, and is why CQT is
preferred for music.** **Wigner-Ville** has excellent resolution and ⚠️ **cross-term
artifacts that look like real components.** **Mel spectrograms** warp frequency
perceptually and are the standard input representation for speech ML (§8 → `dsp-audio-rf-and-images`).

**7.3 Parametric methods** — ⚠️ **these beat the fs/N resolution limit by assuming a
model.** **MUSIC** and **ESPRIT** for sinusoids in noise (the basis of direction-of-arrival
estimation), **AR/Burg** modelling, **matrix pencil**. ⚠️ **The catch: if the model order
is wrong or the model doesn't fit, they produce confident nonsense** — spurious peaks that
look exactly like real ones.

**7.4 Detection and estimation.** **Matched filtering** (§4), **CFAR detectors** for radar,
**ROC curves** for the detection/false-alarm trade, and **the Cramér–Rao bound** —
⚠️ **which tells you the best variance any unbiased estimator can achieve, so you know when
to stop trying to improve your estimator.**
