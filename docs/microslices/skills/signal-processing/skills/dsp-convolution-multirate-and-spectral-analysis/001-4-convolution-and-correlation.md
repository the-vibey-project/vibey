---
id: skill-4-convolution-and-correlation-17d24a81fa
purpose: 4 convolution and correlation
source: src/vibey_tools/skills/plugins/signal-processing/skills/dsp-convolution-multirate-and-spectral-analysis/SKILL.md
requires: []
links: ["skill-5-multirate-098a663cdc"]
---

## §4. Convolution and Correlation

**[DURABLE] Convolution is what a linear time-invariant system *does*.** Output = input
convolved with impulse response. ⚠️ **Everything in §3 → `dsp-sampling-frequency-domain-and-filters` is convolution.**

**The convolution theorem**: convolution in time is multiplication in frequency.
**Practically: for long filters, FFT-based convolution beats direct convolution** —
crossover typically around 50–100 taps depending on implementation.
**⚠️ Overlap-add and overlap-save** are how you apply FFT convolution to a continuous
stream without processing the whole signal at once. **Partitioned convolution** gives you
low latency with long impulse responses — ⚠️ **which is how real-time convolution reverb
with a multi-second impulse response is possible at all.**

**⚠️ Circular vs. linear convolution is the classic FFT bug**: the FFT gives you circular
convolution, which wraps around. **Zero-pad both inputs to at least N+M-1** or your output
is corrupted at the edges in a way that looks like a subtle artifact rather than an error.

**Correlation** is convolution with one input reversed. **Cross-correlation for time
delay estimation and template matching** (⚠️ **and GCC-PHAT is the standard for acoustic
time-difference-of-arrival**), **autocorrelation for periodicity and pitch**, and
**matched filtering** — ⚠️ **provably optimal for detecting a known signal in white noise,
and the basis of radar, sonar, and GPS.**

---
