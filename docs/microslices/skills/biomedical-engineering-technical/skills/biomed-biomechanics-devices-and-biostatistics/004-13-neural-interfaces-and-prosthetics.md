---
id: skill-13-neural-interfaces-and-prosthetics-86bf595f85
purpose: 13 neural interfaces and prosthetics
source: src/vibey_tools/skills/plugins/biomedical-engineering-technical/skills/biomed-biomechanics-devices-and-biostatistics/SKILL.md
requires: ["skill-12-tissue-engineering-586d86e0b2"]
links: ["skill-14-lab-automation-and-instrumentation-841743ba70"]
---

## §13. Neural Interfaces and Prosthetics

### 13.1 Recording

| Modality | Bandwidth | Invasiveness | Longevity |
|---|---|---|---|
| **EEG (scalp)** | ⚠️ **low; spatially blurred by skull** | none | indefinite |
| **ECoG** | good | subdural | years |
| **Intracortical (Utah array)** | ⚠️ **single-unit** | penetrating | ⚠️ **months–years, degrading** |
| **Peripheral nerve cuff** | moderate | surgical | — |
| **EMG (surface / implanted)** | good for prosthetics | low | — |

**⚠️ The chronic-recording failure mode is the foreign body response** (§11): glial
scarring encapsulates the electrode, impedance rises, and **signal amplitude decays over
months.** **This — not the electronics — is the limiting factor on intracortical BCI
longevity**, and flexible/soft electrodes exist specifically to reduce the mechanical
mismatch driving it.

### 13.2 Signal chain
```
Spike detection (threshold on 300–6000 Hz band, typically −4 to −5×RMS noise)
  → spike sorting (PCA/template matching, ⚠️ or "threshold crossings" used directly,
    since much BCI decoding works fine without sorting)
    → binned firing rates (⚠️ typically 20–50 ms bins)
      → decoder
```
**Decoders**: **population vector**, **Wiener filter**, **Kalman filter** (⚠️ **the
workhorse for cursor and reach decoding — smooth, causal, and it handles the latent-state
structure naturally**), and recurrent networks.
**⚠️ Non-stationarity is the operational problem**: units appear and disappear day to day.
**Recalibration, or decoders designed to be robust to unit turnover, are required.**

**EEG BCI paradigms**: **P300** (⚠️ **~300 ms positive deflection to an oddball —
requires averaging over repetitions, so it's slow**), **SSVEP** (⚠️ **frequency-tagged
flicker; high information rate and needs no training**), and **motor imagery**
(⚠️ **event-related desynchronization in µ/β bands; the CSP + LDA pipeline is the classic
baseline, and a substantial fraction of users cannot drive it — "BCI illiteracy"**).

### 13.3 Prosthetic control
**Direct EMG** — amplitude envelope drives velocity. **Pattern recognition** over EMG
features (⚠️ **time-domain features — MAV, zero crossings, waveform length, slope sign
changes — plus LDA remains a very strong baseline**). **Targeted muscle reinnervation**
surgically redirects amputated nerves to spare muscle, creating intuitive control sites.

**⚠️ The sensory problem is as important as the motor one**: without proprioception and
touch, users must watch the limb constantly, and rejection rates for advanced prostheses
are high. **Sensory feedback via nerve stimulation is where the field's leverage is.**

**Control latency budget: ⚠️ under ~100–125 ms end-to-end**, or the coupling feels wrong
and performance degrades.

---
