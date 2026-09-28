---
id: skill-18-transmission-lines-35c11fc111
purpose: 18 transmission lines
source: src/vibey_tools/skills/plugins/electromagnetism-and-electricity/skills/em-maxwell-waves-transmission-lines-and-relativity/SKILL.md
requires: ["skill-17-electromagnetic-waves-97210391d8"]
links: ["skill-19-magnetism-as-relativistic-electrostatics-b94cd43cbd"]
---

## §18. Transmission Lines

**⚠️ Once a circuit is comparable to a wavelength** (§9 → `em-current-energy-flow-circuits-and-ac`), ⚠️ **voltage and current vary
ALONG the line and you must treat it as distributed.**
```
⚠️ CHARACTERISTIC IMPEDANCE  Z₀ = √(L/C) per unit length —
   ⚠️ a GEOMETRIC property, not a resistance. A 50 Ω cable does not
   dissipate; it presents 50 Ω to a wave
⚠️ REFLECTION  Γ = (Z_L − Z₀)/(Z_L + Z₀)
   ⚠️ Open circuit → Γ = +1 · Short → Γ = −1 · Matched → Γ = 0
⚠️ VSWR · standing waves · ⚠️ the Smith chart as the classic tool
⚠️ VELOCITY FACTOR  signals travel slower than c in dielectric
```
**⚠️ Why 50 Ω and 75 Ω exist**: ⚠️ **in coax, minimum loss and maximum power handling occur
at different impedances (~77 Ω and ~30 Ω respectively), and 50 Ω is roughly the
compromise; 75 Ω is the low-loss choice used for video and broadcast.**
**⚠️ Digital designers meet this constantly**: ⚠️ **fast edges have high-frequency content
regardless of clock rate, so PCB traces become transmission lines, and ringing and
overshoot are reflections from impedance mismatch — fixed by termination, not by
"slowing things down."**

---
