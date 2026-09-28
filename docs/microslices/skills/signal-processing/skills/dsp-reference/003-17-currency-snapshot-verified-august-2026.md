---
id: skill-17-currency-snapshot-verified-august-2026-65cc48ff8c
purpose: 17 currency snapshot verified august 2026
source: src/vibey_tools/skills/plugins/signal-processing/skills/dsp-reference/SKILL.md
requires: ["skill-16-contested-questions-73effb9b78"]
links: ["skill-18-the-canon-ce48fe0a1b"]
---

## §17. Currency Snapshot — verified August 2026

**[DURABLE] Almost none of this document moves.** Nyquist 1928, Shannon 1949,
Cooley–Tukey 1965, Ephraim–Malah 1985. **§1–§7 → `dsp-sampling-frequency-domain-and-filters`, `dsp-convolution-multirate-and-spectral-analysis` and §9–§15 → `dsp-audio-rf-and-images`, `dsp-implementation-tools-and-testing` are stable.** Here is what
changed.

| Thing | Status as of Aug 2026 | Decay risk |
|---|---|---|
| **⚠️ Opus + ML** | **Opus 1.5 (March 2024, Xiph.Org) put machine learning inside the codec for the first time** — all **decoder-side**, so services can adopt playback-side alone. **Deep PLC** (neural reconstruction of lost packets, for occasional loss); **DRED** (for burst loss); **LACE/NoLACE** (DNN post-filter denoising). Opus is **mandatory in WebRTC** | Low (dated) |
| **DRED mechanics** | **Rate-distortion-optimized VAE** compressing acoustic parameters: **up to ~1 second of redundancy at ~12–32 kb/s overhead**, carried in packet padding; each 20 ms packet effectively transmitted many times over. **20 acoustic features — 18 Bark-frequency cepstral coefficients (bands matching CELT) plus pitch and voicing.** ⚠️ **No waveform or phase information, so recovered speech "will significantly deviate from the original waveform, despite sounding similar."** Trained against realistic burst-loss traces from Microsoft's Audio Deep PLC Challenge, plus a generative loss model **under 10,000 parameters** | Low |
| **⚠️ Opus 1.6** | **Released December 2025.** Adds **bandwidth extension (BWE)**, extending the FARGAN wideband vocoder used by deep PLC and DRED — ⚠️ **enabling DRED to reach fullband quality**, and **NoLACE + BWE giving good fullband speech as low as 9 kb/s.** Many DRED improvements over 1.5 | Medium |
| **⚠️ DRED standardization** | **IETF `draft-ietf-mlcodec-opus-dred`** — draft **-05 dated January 2026**, expiring July 2026. ⚠️ **As of 2026 the format is still being finalised: treat DRED as advanced rather than settled** | **High** |
| **The DNN-in-codec barrier** | ⚠️ **Opus's developers name model size — "even more than complexity" — as one of the main barriers to using DNNs in codecs.** Independent evaluation notes any AI/ML use "is bound to significantly increase the real-time computational requirements" | Medium |
| **Speech enhancement** | **RNNoise (Valin, 2018)** remains the landmark hybrid: a 4-hidden-layer network estimates **ideal critical-band gains** while **a traditional pitch filter attenuates noise between harmonics** — beating a classical MMSE spectral estimator at real-time 48 kHz on a low-power CPU. **DeepFilterNet** and successors **predict linear filters instead of estimating clean speech**, for edge deployability. ⚠️ **Current honest read: traditional methods are "fast but conservative"; deep learning is "more aggressive while preserving speech quality, at the cost of higher computational requirements"** | Medium |
| **Echo cancellation** | ⚠️ **Notably, most state-of-the-art AEC remains classical DSP or hybrid DSP-ML** — delay estimator and adaptive linear filter classical, **DNNs typically replacing only the nonlinear residual echo suppressor.** End-to-end neural AEC is an active research direction, not the default | Medium |
| **Hearing aids** | Real-time multichannel deep enhancement compared against adaptive differential microphones and binaural beamforming: ⚠️ **all approaches perform similarly in diffuse noise; the binaural deep approach wins in the presence of spatial interferers.** Deep models for hearing aids require **processing delay of only a few milliseconds** | Medium |

**Goes stale fastest:** the DRED standardization status and the neural-enhancement
frontier. **Essentially never stale:** §1–§7 → `dsp-sampling-frequency-domain-and-filters`, `dsp-convolution-multirate-and-spectral-analysis`, §9–§15 → `dsp-audio-rf-and-images`, `dsp-implementation-tools-and-testing`.

---
