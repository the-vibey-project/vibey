---
id: skill-5-multirate-098a663cdc
purpose: 5 multirate
source: src/vibey_tools/skills/plugins/signal-processing/skills/dsp-convolution-multirate-and-spectral-analysis/SKILL.md
requires: ["skill-4-convolution-and-correlation-17d24a81fa"]
links: ["skill-6-adaptive-filtering-and-estimation-ba3770d0cf"]
---

## §5. Multirate

**[DURABLE] Changing sample rate correctly, which people routinely get wrong.**

**Decimation (downsampling by M)**: ⚠️ **low-pass filter FIRST, then discard samples.**
Skipping the filter aliases (§1.1 → `dsp-sampling-frequency-domain-and-filters`). **Interpolation (upsampling by L)**: insert zeros, then
low-pass to remove the spectral images. **Rational resampling by L/M**: upsample, filter
once, downsample — ⚠️ **and the single filter does both jobs; don't do it in two stages.**

**Polyphase decomposition** restructures this so you never compute samples you're about to
discard — ⚠️ **an M-fold efficiency win, and it's what every real resampler does.**

**⚠️ Arbitrary-ratio resampling** (44.1 → 48 kHz, the classic) needs fractional-delay
interpolation — **Farrow structures, or windowed-sinc interpolation.** ⚠️ **Quality varies
enormously between implementations; a cheap resampler is an audible one.** Libraries:
**libsamplerate/SoX/r8brain** for audio, `scipy.signal.resample_poly` (⚠️ **use
`resample_poly`, not `resample` — the latter assumes periodicity and rings at the edges**).

**Related structures**: **CIC filters** (⚠️ **multiplier-free, the standard front end in
sigma-delta and SDR hardware**), **half-band filters** (half the taps are zero),
**filter banks and the STFT** as a multirate system (§7).

---
