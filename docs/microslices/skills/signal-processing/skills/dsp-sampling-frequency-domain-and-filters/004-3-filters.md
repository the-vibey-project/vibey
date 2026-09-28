---
id: skill-3-filters-383232bb66
purpose: 3 filters
source: src/vibey_tools/skills/plugins/signal-processing/skills/dsp-sampling-frequency-domain-and-filters/SKILL.md
requires: ["skill-2-the-frequency-domain-8aebb3502f"]
links: []
---

## §3. Filters

**[DURABLE] The core tool. Choose the class first, then the design method.**

### 3.1 FIR vs. IIR — the decision that matters

| | **FIR** | **IIR** |
|---|---|---|
| Feedback | None | Yes |
| **Stability** | ⚠️ **Always stable** | ⚠️ **Can be unstable; must check poles** |
| **Phase** | ⚠️ **Exactly linear phase available** (symmetric taps) | Nonlinear phase; group delay varies |
| Order for a given sharpness | ⚠️ **Much higher** | Much lower — often 10× fewer coefficients |
| Fixed-point behaviour | Well-behaved | ⚠️ **Coefficient quantization can destabilize** |
| Analogue equivalent | None | Butterworth, Chebyshev, Elliptic, Bessel |

**⚠️ The decision rule**: **linear phase required (audio, images, anything where waveform
shape matters)? FIR.** **Tight compute budget and phase doesn't matter (control loops,
simple smoothing)? IIR.**

### 3.2 Design

**FIR methods**: **windowed sinc** (simple, adequate), **Parks–McClellan / Remez**
(⚠️ **optimal equiripple for a given order — the professional default**), **least
squares**, **frequency sampling**.

**IIR methods**: design in the analogue domain and transform — **bilinear transform**
(⚠️ **warps frequency; pre-warp your critical frequencies or your cutoff lands in the wrong
place**), or **impulse invariance**. The classical families: **Butterworth** (maximally
flat passband), **Chebyshev I/II** (ripple traded for steeper rolloff), **Elliptic**
(steepest, ripple everywhere), **Bessel** (⚠️ **maximally flat *group delay* — the one to
use when waveform shape matters more than magnitude**).

**⚠️ Always implement high-order IIR as cascaded second-order sections (biquads / SOS).**
A direct-form high-order IIR is numerically fragile and can be unstable purely from
coefficient quantization. ⚠️ **`scipy.signal` defaults to transfer-function output for
historical reasons — ask for `output='sos'`.**

### 3.3 The specifics worth knowing
**Group delay** is the derivative of phase — ⚠️ **it's what actually smears your waveform,
and it's frequency-dependent for IIR.** **Filtfilt / zero-phase filtering** runs the filter
forwards and backwards to cancel phase — ⚠️ **excellent offline, impossible in real time,
and it squares the magnitude response** (so your -3 dB point moves). **Transient response**
at startup matters for short signals. And the everyday filters: **moving average**
(⚠️ **the crudest low-pass; its frequency response is a sinc with poor stopband**),
**exponential/one-pole** (cheap, adequate), **median** (nonlinear; ⚠️ **excellent for
impulsive noise where linear filters smear it**), **Savitzky–Golay** (⚠️ **smooths while
preserving peak shape — the right choice for spectroscopy and chromatography**),
**notch** for mains hum, **DC blocker**, **all-pass** for phase shaping.
