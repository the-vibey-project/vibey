---
id: skill-11-power-rms-and-power-factor-30fda20587
purpose: 11 power rms and power factor
source: src/vibey_tools/skills/plugins/electromagnetism-and-electricity/skills/em-current-energy-flow-circuits-and-ac/SKILL.md
requires: ["skill-10-ac-and-impedance-220fbadecd"]
links: []
---

## §11. Power, RMS and Power Factor

**⚠️ RMS is defined so that an AC quantity delivers the same average power into a resistor
as a DC quantity of the same value** — ⚠️ **for a sine, V_rms = V_peak/√2, which is where
the ~0.707 factor comes from.** **⚠️ It is NOT the average of the waveform, and it differs
for non-sinusoidal waveforms.**
```
⚠️ REAL power P (W) — actually dissipated
⚠️ REACTIVE power Q (VAR) — ⚠️ sloshes back and forth, dissipates nothing,
   ⚠️ AND STILL CAUSES I²R LOSSES IN THE WIRES. That's why it matters
⚠️ APPARENT power S (VA) = VI ;  ⚠️ POWER FACTOR = P/S
```
**⚠️ Power factor correction** exists because ⚠️ **the distribution system must be sized for
APPARENT power while only real power is billed to many customers** — **hence industrial PF
penalties.**
**⚠️ Harmonics and non-linear loads**: ⚠️ **switch-mode supplies draw current in pulses, so
PF can be poor even with voltage and current "in phase," and ⚠️ triplen harmonics ADD in
the neutral of a three-phase system rather than cancelling — which is why neutrals in
harmonic-rich installations can carry more current than the phases.**

---

# PART III — MAGNETISM
