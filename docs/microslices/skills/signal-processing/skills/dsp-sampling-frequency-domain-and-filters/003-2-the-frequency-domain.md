---
id: skill-2-the-frequency-domain-8aebb3502f
purpose: 2 the frequency domain
source: src/vibey_tools/skills/plugins/signal-processing/skills/dsp-sampling-frequency-domain-and-filters/SKILL.md
requires: ["skill-1-sampling-and-quantization-cb9dfd8f79"]
links: ["skill-3-filters-383232bb66"]
---

## §2. The Frequency Domain

### 2.1 The transforms

**[DURABLE]** **Fourier series** (periodic), **Fourier transform** (continuous, infinite),
**DTFT** (discrete-time, continuous frequency), **DFT** (discrete both — ⚠️ **what you can
actually compute**), and the **FFT**, which is an algorithm for the DFT, not a different
transform. **O(n log n) versus O(n²)** — and that reduction is arguably the single most
consequential algorithm in engineering.

**Related transforms**: **DCT** (real-valued, energy-compacting — ⚠️ **the basis of JPEG
and MP3/AAC**), **MDCT** (overlapping, critically sampled — ⚠️ **what modern audio codecs
actually use**), **Hilbert** (analytic signal, envelope, instantaneous phase),
**wavelets** (multi-resolution — §7 → `dsp-convolution-multirate-and-spectral-analysis`), and the **Z-transform** (the discrete analogue of
Laplace, and the language of filter design — §3).

### 2.2 ⚠️ The DFT facts that bite

> **⚠️ GOTCHA — every one of these produces a wrong plot that looks plausible:**
> - **⚠️ The DFT assumes your signal is periodic with period N.** It isn't. The
>   discontinuity between the last sample and the first creates **spectral leakage** —
>   energy smeared across all bins.
> - **Windowing is the mitigation, and it has a cost.** Multiplying by a taper (Hann,
>   Hamming, Blackman–Harris, Kaiser) reduces leakage **and widens the main lobe**, so you
>   trade frequency resolution for dynamic range. ⚠️ **Rectangular (no window) has the
>   narrowest main lobe and the worst sidelobes — it's the right choice only when your
>   signal is genuinely periodic in the window.**
> - **Bin spacing is fs/N.** ⚠️ **A frequency between bins spreads across neighbours —
>   "scalloping loss."** This is why a pure tone rarely shows as a single clean spike.
> - **⚠️ Zero-padding does not add resolution.** It interpolates the spectrum — smoother
>   plot, same underlying resolution. **The resolution is set by the observation duration,
>   full stop.**
> - **Normalization conventions differ between libraries** — where the 1/N goes.
>   ⚠️ **Check before comparing magnitudes across tools.**
> - **Real input → conjugate-symmetric spectrum.** Use `rfft` and halve your work.
> - **⚠️ The FFT is fastest for highly composite N** (powers of two ideally). A prime N
>   falls back to a slower path — in older or naive implementations, dramatically slower.

### 2.3 Frequency resolution
**Δf = fs/N = 1/T**, where **T is the observation duration.** ⚠️ **This is the whole story:
to resolve two tones 1 Hz apart you need at least one second of data.** No window, no
zero-padding, and no algorithm changes it — though **parametric methods (§7.3 → `dsp-convolution-multirate-and-spectral-analysis`) can beat it
by assuming a model.**

### 2.4 The uncertainty trade
**[DURABLE] Δt · Δf ≥ constant.** Short windows localize events in time and blur them in
frequency; long windows do the reverse. ⚠️ **Every spectrogram you have ever looked at is a
choice on this curve**, and picking the window length is the main design decision in
time-frequency analysis (§7 → `dsp-convolution-multirate-and-spectral-analysis`).

---
