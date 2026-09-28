---
id: skill-13-testing-and-debugging-dsp-71e8245439
purpose: 13 testing and debugging dsp
source: src/vibey_tools/skills/plugins/signal-processing/skills/dsp-implementation-tools-and-testing/SKILL.md
requires: ["skill-12-tools-1df57576ad"]
links: ["skill-14-sensors-and-physical-signals-c188047cd9"]
---

## §13. Testing and Debugging DSP

**[DURABLE] The discipline, and it's underdeveloped in most codebases.**

**⚠️ Test with known signals first, always**: an impulse (gives you the impulse response
directly), a step, a pure sine at a known frequency and amplitude, white noise (⚠️ **which
should give you a flat spectrum — if it doesn't, your analysis is wrong before your
algorithm is**), and a **chirp/sweep** to get the frequency response in one shot.

**Verify the properties you can check cheaply**: **Parseval's theorem** (⚠️ **energy in
time equals energy in frequency — a superb catch-all for scaling and normalization bugs**),
**linearity and time-invariance** where they should hold, **DC gain**, **group delay**, and
**round-trip identity** (analyze then synthesize should reconstruct).

**⚠️ Look at the signal.** Plot the waveform, the spectrum, and the spectrogram. **Most DSP
bugs are instantly visible and invisible in numbers** — and for audio, **listen to it**.
The ear detects artifacts that no metric flags.

**⚠️ The specific bugs to check for first**: **off-by-one in window alignment or overlap**;
**scaling factors** from FFT normalization; **edge effects** at buffer boundaries
(⚠️ **the classic: filter state not carried between blocks, giving a click at every block
boundary**); **circular convolution wraparound** (§4 → `dsp-convolution-multirate-and-spectral-analysis`); **complex conjugate and sign
conventions**; **and phase unwrapping**.

**Metrics**: SNR, THD, THD+N, SINAD, ENOB for converters; **PESQ, POLQA, STOI, SI-SDR**
for speech quality — ⚠️ **and the honest caveat that these correlate imperfectly with human
judgement, which is why subjective MOS testing persists.**

---
