---
id: skill-1-sampling-and-quantization-cb9dfd8f79
purpose: 1 sampling and quantization
source: src/vibey_tools/skills/plugins/signal-processing/skills/dsp-sampling-frequency-domain-and-filters/SKILL.md
requires: ["skill-0-routing-91d6f0b8db"]
links: ["skill-2-the-frequency-domain-8aebb3502f"]
---

## §1. Sampling and Quantization

**[DURABLE] The foundation, and the source of the most expensive mistakes.**

### 1.1 Nyquist–Shannon

**A signal band-limited to B Hz is perfectly reconstructable from samples taken at
> 2B Hz.** ⚠️ **Note the strictness: strictly greater than, and strictly band-limited.**

> **⚠️ GOTCHA — aliasing, and why it's the worst bug in this document.** Frequency
> components above Nyquist **do not disappear — they fold back and appear as lower
> frequencies that are indistinguishable from real signal.** A 30 kHz tone sampled at
> 44.1 kHz appears at 14.1 kHz. **It looks like data. It is not.**
>
> **⚠️ The fix must happen in the analog domain, before the ADC.** An **anti-aliasing
> filter** is a hardware component. **Once aliased, always aliased** — there is no
> software repair, and this is the single most important operational fact in DSP.
>
> **The same applies when you downsample in software** (§5 → `dsp-convolution-multirate-and-spectral-analysis`): ⚠️ **decimating without
> low-pass filtering first is aliasing you inflicted on yourself.**

**⚠️ And the corollaries people miss**: sampling a signal that isn't band-limited
(virtually everything real) aliases the noise floor too; **sampling exactly at 2B is not
enough** (a sine sampled at its zero crossings gives you nothing); and **jitter in the
sample clock is itself a noise source** — timing uncertainty translates directly into
amplitude error, and it dominates at high frequencies.

**Oversampling** deliberately samples well above Nyquist to relax the analog filter
requirements and spread quantization noise over a wider band. **Sigma-delta converters**
push this to an extreme with noise shaping — ⚠️ **which is why a 1-bit converter at very
high rate can outperform a 16-bit converter at Nyquist.**

### 1.2 Quantization

**[DURABLE] Amplitude discretization.** The rule of thumb: **~6 dB of SNR per bit.**
16-bit ≈ 96 dB, 24-bit ≈ 144 dB (⚠️ **in theory — real converters are limited by analog
noise well before that**).

**⚠️ Quantization error is only noise-like if the signal is busy enough.** For quiet or
slowly-varying signals it becomes **correlated with the signal and audible as distortion**.
**Dither** — adding a small amount of noise before quantizing — **decorrelates the error
and trades distortion for a slightly raised noise floor.** ⚠️ **It sounds absurd and it is
correct: adding noise makes it sound better.** **Noise shaping** pushes that noise into
frequency bands where it matters less perceptually.

**Also**: **clipping** is a hard nonlinearity that generates broadband harmonics —
⚠️ **leave headroom**; **DC offset** eats dynamic range and breaks many algorithms
(high-pass it out); and **float vs. fixed** is §11 → `dsp-implementation-tools-and-testing`.

---
