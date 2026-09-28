---
id: skill-15-sampling-and-dsp-essentials-c59f03228b
purpose: 15 sampling and dsp essentials
source: src/vibey_tools/skills/plugins/radio-technology-for-software-devs/skills/radio-spread-spectrum-ofdm-access-and-sdr/SKILL.md
requires: ["skill-14-sdr-and-iq-sampling-6577dfeb0e"]
links: ["skill-16-sdr-toolchain-9ce2b4f6ae"]
---

## §15. Sampling and DSP Essentials

```
⚠️ NYQUIST      sample rate must exceed 2× the signal BANDWIDTH.
   ⚠️ For complex/IQ sampling, sample rate = bandwidth (not 2×) —
   the complex representation already carries the sign of frequency
ALIASING        ⚠️ under-sampled content folds back and is indistinguishable
   from real signal. Anti-alias filtering is mandatory, not optional
DECIMATION      ⚠️ filter THEN downsample. Downsampling without filtering
   first aliases — the single most common beginner DSP bug
INTERPOLATION   upsample and filter
FFT             ⚠️ time → frequency. Bin width = sample rate / FFT size.
   ⚠️ WINDOWING (Hann, Blackman) reduces spectral leakage from the implicit
   rectangular window; without it a strong tone smears across bins
FILTERS         FIR (⚠️ linear phase, stable, more taps) vs IIR (efficient,
   phase distortion). ⚠️ For radio, linear phase usually matters
```
**⚠️ The receive chain in software, in order**: **tune → sample (IQ) → filter to the
signal's bandwidth → decimate → correct frequency offset → time-synchronize → equalize →
demodulate to symbols → decode (FEC) → deframe → CRC.**
⚠️ **Synchronization is where most of the difficulty lives.** **Your oscillator and theirs
disagree — carrier frequency offset, sample timing offset, and phase — and estimating and
tracking those is the bulk of a real demodulator.**

---
