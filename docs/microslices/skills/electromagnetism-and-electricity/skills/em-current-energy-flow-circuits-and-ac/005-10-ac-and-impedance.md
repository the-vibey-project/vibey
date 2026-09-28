---
id: skill-10-ac-and-impedance-220fbadecd
purpose: 10 ac and impedance
source: src/vibey_tools/skills/plugins/electromagnetism-and-electricity/skills/em-current-energy-flow-circuits-and-ac/SKILL.md
requires: ["skill-9-circuit-theory-and-its-validity-550f5a05b9"]
links: ["skill-11-power-rms-and-power-factor-30fda20587"]
---

## §10. AC and Impedance

**⚠️ Sinusoids are special because they are the EIGENFUNCTIONS of linear time-invariant
systems** — ⚠️ **a sinusoid in gives a sinusoid out at the same frequency, changed only in
amplitude and phase.** **That's why phasors work and why Fourier analysis is the right
tool.**
```
⚠️ IMPEDANCE Z = R + jX
   ⚠️ RESISTOR  Z = R          (in phase)
   ⚠️ INDUCTOR  Z = jωL        (⚠️ voltage LEADS current by 90°)
   ⚠️ CAPACITOR Z = 1/(jωC)    (⚠️ current LEADS voltage by 90°)
   ⚠️ REACTANCE stores and returns energy; it does NOT dissipate
⚠️ RESONANCE at ω₀ = 1/√(LC); ⚠️ Q sets bandwidth and selectivity
```
**⚠️ Filters** (**low/high/band-pass, and ⚠️ the −3 dB point as the conventional corner**),
**and ⚠️ Bode plots as the standard way to see it.**
**⚠️ The mnemonic "ELI the ICE man"** — ⚠️ **in an inductor (L), E leads I; in a capacitor
(C), I leads E.**

---
