---
id: skill-15-anti-patterns-3bb9109b0a
purpose: 15 anti patterns
source: src/vibey_tools/skills/plugins/signal-processing/skills/dsp-reference/SKILL.md
requires: []
links: ["skill-16-contested-questions-73effb9b78"]
---

## §15. Anti-Patterns

| Anti-pattern | Why |
|---|---|
| **Sampling without an analogue anti-aliasing filter** | ⚠️ **Irreversible. Nothing downstream fixes it** (§1.1 → `dsp-sampling-frequency-domain-and-filters`) |
| Downsampling without low-pass filtering first | ⚠️ **Self-inflicted aliasing** (§5 → `dsp-convolution-multirate-and-spectral-analysis`) |
| Sampling exactly at 2×B | Nyquist is a strict inequality (§1.1 → `dsp-sampling-frequency-domain-and-filters`) |
| Ignoring sample-clock jitter | Timing uncertainty becomes amplitude noise (§1.1 → `dsp-sampling-frequency-domain-and-filters`) |
| Quantizing without dither on quiet signals | Error correlates with signal → audible distortion (§1.2 → `dsp-sampling-frequency-domain-and-filters`) |
| No headroom | Clipping generates broadband harmonics (§1.2 → `dsp-sampling-frequency-domain-and-filters`) |
| Assuming zero-padding adds resolution | ⚠️ **It interpolates. Resolution = 1/T** (§2.2 → `dsp-sampling-frequency-domain-and-filters`) |
| Rectangular window on a non-periodic signal | Spectral leakage across all bins (§2.2 → `dsp-sampling-frequency-domain-and-filters`) |
| Comparing FFT magnitudes across libraries | Normalization conventions differ (§2.2 → `dsp-sampling-frequency-domain-and-filters`) |
| A single periodogram as a spectral estimate | ⚠️ **Variance doesn't shrink with data. Use Welch** (§7.1 → `dsp-convolution-multirate-and-spectral-analysis`) |
| High-order IIR in direct form | ⚠️ **Numerically fragile. Use cascaded biquads/SOS** (§3.2 → `dsp-sampling-frequency-domain-and-filters`) |
| Bilinear transform without pre-warping | Your cutoff lands in the wrong place (§3.2 → `dsp-sampling-frequency-domain-and-filters`) |
| `filtfilt` in a real-time path | Non-causal by construction (§3.3 → `dsp-sampling-frequency-domain-and-filters`) |
| Moving average as a serious low-pass | Sinc response, poor stopband (§3.3 → `dsp-sampling-frequency-domain-and-filters`) |
| Linear filter for impulsive noise | ⚠️ **It smears it. Use a median filter** (§3.3 → `dsp-sampling-frequency-domain-and-filters`) |
| FFT convolution without zero-padding to N+M-1 | ⚠️ **Circular wraparound corrupts the edges** (§4 → `dsp-convolution-multirate-and-spectral-analysis`) |
| Not carrying filter state across blocks | ⚠️ **A click at every block boundary** (§13 → `dsp-implementation-tools-and-testing`) |
| `scipy.signal.resample` for audio | Assumes periodicity; rings at the edges. Use `resample_poly` (§5 → `dsp-convolution-multirate-and-spectral-analysis`) |
| LMS step size chosen by guess | Diverges or never converges (§6 → `dsp-convolution-multirate-and-spectral-analysis`) |
| Echo cancellation without double-talk detection | ⚠️ **The filter destroys itself when both sides speak** (§6 → `dsp-convolution-multirate-and-spectral-analysis`, §8.3 → `dsp-audio-rf-and-images`) |
| Parametric spectral estimate with wrong model order | ⚠️ **Confident spurious peaks** (§7.3 → `dsp-convolution-multirate-and-spectral-analysis`) |
| Wigner-Ville cross-terms read as real components | Artifacts of the transform (§7.2 → `dsp-convolution-multirate-and-spectral-analysis`) |
| Allocation, locks, or logging in the audio callback | Hard real-time thread → dropouts (§11 → `dsp-implementation-tools-and-testing`) |
| Ignoring denormals in a decaying IIR | ⚠️ **CPU spikes when the signal goes quiet** (§11 → `dsp-implementation-tools-and-testing`) |
| Fixed-point port without simulating first | Coefficient quantization can destabilize IIR (§11 → `dsp-implementation-tools-and-testing`) |
| Wraparound instead of saturating arithmetic | A loud sound becomes a horrible one (§11 → `dsp-implementation-tools-and-testing`) |
| Trusting PESQ/STOI as ground truth | ⚠️ **They correlate imperfectly with human judgement** (§13 → `dsp-implementation-tools-and-testing`) |
| Never plotting the spectrogram | ⚠️ **Most DSP bugs are visible and only visible** (§13 → `dsp-implementation-tools-and-testing`) |
| Never listening to the audio | The ear catches what metrics miss (§13 → `dsp-implementation-tools-and-testing`) |
| Replacing a working DSP block with a neural net wholesale | ⚠️ **The evidence favours hybrids** (§8.3 → `dsp-audio-rf-and-images`, §16.1) |
| Assuming a neural enhancer is free | ⚠️ **DNNs significantly raise real-time compute** (§8.2 → `dsp-audio-rf-and-images`) |

---
