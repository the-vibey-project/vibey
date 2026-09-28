---
id: skill-19-quick-reference-7f9cab3790
purpose: 19 quick reference
source: src/vibey_tools/skills/plugins/signal-processing/skills/dsp-reference/SKILL.md
requires: ["skill-18-the-canon-ce48fe0a1b"]
links: ["skill-20-sources-and-method-4d71d07fe8"]
---

## §19. Quick Reference

### 19.1 Numbers
- **Nyquist: fs > 2B**, strictly
- **Frequency resolution Δf = fs/N = 1/T** — ⚠️ **set by duration, nothing else**
- **~6 dB SNR per bit**; 16-bit ≈ 96 dB
- **Hearing: 20 Hz – 20 kHz, ~120 dB**
- **Musician latency threshold ≈ 10 ms**; conversational ≈ 150–200 ms one-way
- **FFT convolution beats direct at roughly 50–100 taps**
- **Zero-pad convolution to ≥ N+M-1**
- **Shannon: C = B log₂(1 + SNR)** — a hard ceiling

### 19.2 Method picker
| Need | Use |
|---|---|
| Remove a specific frequency | Notch filter (§3.3 → `dsp-sampling-frequency-domain-and-filters`) |
| Smooth without distorting peaks | **Savitzky–Golay** (§3.3 → `dsp-sampling-frequency-domain-and-filters`) |
| Remove impulsive noise | **Median filter** — not linear (§3.3 → `dsp-sampling-frequency-domain-and-filters`) |
| Linear phase required | **FIR** (§3.1 → `dsp-sampling-frequency-domain-and-filters`) |
| Tight compute, phase irrelevant | **IIR biquads** (§3.1 → `dsp-sampling-frequency-domain-and-filters`) |
| Flat group delay | **Bessel** (§3.2 → `dsp-sampling-frequency-domain-and-filters`) |
| Sharpest transition for the order | **Elliptic** (§3.2 → `dsp-sampling-frequency-domain-and-filters`) |
| Offline, want zero phase | `filtfilt` (§3.3 → `dsp-sampling-frequency-domain-and-filters`) |
| Estimate a spectrum | **Welch**, or multitaper (§7.1 → `dsp-convolution-multirate-and-spectral-analysis`) |
| Resolve close tones with short data | **MUSIC/ESPRIT** — ⚠️ model-dependent (§7.3 → `dsp-convolution-multirate-and-spectral-analysis`) |
| Time-varying spectrum | STFT; **CQT for music** (§7.2 → `dsp-convolution-multirate-and-spectral-analysis`) |
| Change sample rate | **Polyphase resampler** (§5 → `dsp-convolution-multirate-and-spectral-analysis`) |
| Find a known signal in noise | **Matched filter** (§4 → `dsp-convolution-multirate-and-spectral-analysis`) |
| Estimate time delay between mics | **GCC-PHAT** (§4 → `dsp-convolution-multirate-and-spectral-analysis`) |
| Cancel echo | Adaptive filter + residual suppressor + **double-talk detector** (§8.3 → `dsp-audio-rf-and-images`) |
| Suppress noise, low compute | **RNNoise / DeepFilterNet** hybrid (§8.3 → `dsp-audio-rf-and-images`) |
| Multi-mic spatial filtering | **Beamforming** (MVDR/GSC) (§8.3 → `dsp-audio-rf-and-images`) |
| Separate music sources | Neural separator (Demucs) (§8.4 → `dsp-audio-rf-and-images`) |
| Voice over a lossy network | ⚠️ **Opus with Deep PLC / DRED** (§8.2 → `dsp-audio-rf-and-images`) |
| Track a state over time | **Kalman filter** (§6 → `dsp-convolution-multirate-and-spectral-analysis`) |

### 19.3 When it sounds/looks wrong
1. **Plot the spectrogram.** Then **listen** (§13 → `dsp-implementation-tools-and-testing`)
2. **Check for aliasing** — is anything above Nyquist? (§1.1 → `dsp-sampling-frequency-domain-and-filters`)
3. **Check scaling** — Parseval's theorem (§13 → `dsp-implementation-tools-and-testing`)
4. **Check window/overlap alignment** — off-by-one (§13 → `dsp-implementation-tools-and-testing`)
5. **Check filter state across blocks** — clicks at boundaries? (§13 → `dsp-implementation-tools-and-testing`)
6. **Check zero-padding** in FFT convolution (§4 → `dsp-convolution-multirate-and-spectral-analysis`)
7. **Check for clipping and DC offset** (§1.2 → `dsp-sampling-frequency-domain-and-filters`)
8. **Check denormals** if CPU spikes on silence (§11 → `dsp-implementation-tools-and-testing`)
9. **Test with an impulse and a sine** before real data (§13 → `dsp-implementation-tools-and-testing`)

---
