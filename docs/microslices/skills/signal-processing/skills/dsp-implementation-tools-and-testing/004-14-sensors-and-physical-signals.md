---
id: skill-14-sensors-and-physical-signals-c188047cd9
purpose: 14 sensors and physical signals
source: src/vibey_tools/skills/plugins/signal-processing/skills/dsp-implementation-tools-and-testing/SKILL.md
requires: ["skill-13-testing-and-debugging-dsp-71e8245439"]
links: []
---

## §14. Sensors and Physical Signals

**⚠️ The physical layer determines what's possible, and it's often mishandled in
software-first teams.** **Transducer characteristics** — sensitivity, frequency response,
nonlinearity, drift — **bound your entire system**; no filter fixes a bad sensor.
**Calibration** matters and drifts with temperature and time. **Grounding, shielding, and
mains hum** at 50/60 Hz and harmonics are the most common contaminants in instrumentation.
**Anti-aliasing before the ADC** (§1.1 → `dsp-sampling-frequency-domain-and-filters`). **Common-mode rejection** in differential
measurements. **Noise types**: thermal/Johnson (white), shot, **1/f flicker**
(⚠️ **dominant at low frequencies and the reason DC measurements are hard**), and
quantization (§1.2 → `dsp-sampling-frequency-domain-and-filters`).

**Domain notes**: **biomedical** — ECG (baseline wander, mains, muscle artifact), EEG
(⚠️ **microvolt-level, and eye-blink artifacts dominate**), PPG (motion artifact);
**vibration and machinery** — envelope analysis for bearing faults, order tracking;
**seismic and geophysical** — deconvolution; **radar/lidar** — matched filtering and
pulse compression.
