---
id: skill-1-physiological-signal-processing-0db3a4c8cd
purpose: 1 physiological signal processing
source: src/vibey_tools/skills/plugins/biomedical-engineering-technical/skills/biomed-signals-and-medical-imaging/SKILL.md
requires: ["skill-0-routing-c970ef6620"]
links: ["skill-2-medical-imaging-31b02283f5"]
---

## §1. Physiological Signal Processing

### 1.1 The signals and their bands

| Signal | Band | Amplitude | Sampling |
|---|---|---|---|
| **ECG** | 0.05–150 Hz (diagnostic) | 0.1–5 mV | ≥500 Hz diagnostic, 250 monitoring |
| **EEG** | 0.5–100 Hz | ⚠️ **10–100 µV** | 250–1000 Hz |
| **EMG** | 20–500 Hz | 50 µV–5 mV | ≥1000 Hz |
| **PPG** | 0.5–8 Hz | — (AC/DC ratio) | 25–500 Hz |
| **Respiration** | 0.1–2 Hz | — | 25–50 Hz |
| **EOG** | 0.1–30 Hz | 10–100 µV | 250 Hz |
| **Intracortical spikes** | ⚠️ **300–6000 Hz** | 50–500 µV | ⚠️ **≥20–30 kHz** |
| **LFP** | 1–300 Hz | 0.1–1 mV | 1–2 kHz |

**EEG rhythms**: δ 0.5–4, θ 4–8, α 8–13, β 13–30, γ 30–100 Hz.

### 1.2 ⚠️ The filtering constraints that are specific to this domain

**⚠️ Powerline interference (50/60 Hz) sits inside the ECG diagnostic band.** A notch
filter at 60 Hz removes real QRS spectral content — the QRS complex has energy up to
~100 Hz. **A narrow notch rings; a wide notch distorts.** Prefer **adaptive filtering
against a reference sinusoid**, or a very narrow IIR notch applied with zero phase.

**⚠️ Phase distortion changes measured intervals, and intervals are diagnoses.**
A causal high-pass at 0.5 Hz shifts and distorts the **ST segment** — and ST elevation is
myocardial infarction. **The standard fix: zero-phase forward-backward filtering
(`filtfilt`), or a high-pass at 0.05 Hz for diagnostic ECG.**
```
⚠️ Monitoring ECG:  0.5–40 Hz  — acceptable, suppresses wander, NOT diagnostic
⚠️ Diagnostic ECG:  0.05–150 Hz — required for ST analysis
```
**Confusing the two produces plausible, wrong ST measurements.**

**Baseline wander** (respiration, electrode motion, ~0.15–0.3 Hz) — high-pass or
**cubic-spline fitting through the PQ segments**, which avoids filter distortion entirely.

**Motion artifact** overlaps the signal band and cannot be filtered out spectrally.
⚠️ **Use an accelerometer as a reference channel and adaptive-cancel** — this is what
wearable PPG does.

### 1.3 Detection and feature extraction

**Pan–Tompkins QRS detection** — the durable algorithm, and the structure is worth
knowing because it generalizes:
```
bandpass 5–15 Hz  →  differentiate (emphasize slope)  →  square (rectify, emphasize
large)  →  moving-window integrate (~150 ms)  →  adaptive dual thresholds
   + ⚠️ 200 ms refractory (physiologically impossible to have two QRS closer)
   + ⚠️ searchback: if no beat in 1.66× the running RR average, re-search at low threshold
```
**⚠️ The refractory period and searchback are the parts that make it robust** — they encode
physiology as constraints, which is the general lesson.

**HRV** from the RR interval series: **time domain** (SDNN, **RMSSD** — ⚠️ **the
parasympathetic index**, pNN50), **frequency domain** (LF 0.04–0.15 Hz, HF 0.15–0.4 Hz,
LF/HF ratio — ⚠️ **whose interpretation as "sympathovagal balance" is contested**), and
**nonlinear** (Poincaré SD1/SD2, sample entropy, DFA).
**⚠️ RR series are irregularly sampled** — interpolate to a uniform grid before FFT, or use
Lomb–Scargle.

**EEG artifact removal**: **ICA** is the workhorse — ⚠️ **eye blinks and cardiac artifact
separate into identifiable components** with characteristic scalp topographies.
**Regression against EOG channels** for blinks. **ASR (Artifact Subspace
Reconstruction)** for motion.
**⚠️ Reference choice changes everything**: average reference, linked mastoids, or
**Laplacian** — and results are not comparable across reference schemes.

**Time-frequency**, because the signals are non-stationary: **STFT** (⚠️ **fixed
resolution trade — Heisenberg**), **wavelets** (⚠️ **Morlet for EEG oscillations; better
time resolution at high frequency**), **Hilbert–Huang/EMD**, and **multitaper** for
noisy spectral estimates.

---
