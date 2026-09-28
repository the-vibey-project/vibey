---
id: skill-2-diodes-4df2d0fa93
purpose: 2 diodes
source: src/vibey_tools/skills/plugins/digital-logic-and-firmware-engineering/skills/logic-devices-transistors-cmos-gates-and-power/SKILL.md
requires: ["skill-1-the-two-layers-44e3cd10bb"]
links: ["skill-3-transistors-as-switches-30fe96797c"]
---

## §2. ⚠️ Diodes

```
⚠️ THE BEHAVIOUR  ⚠️ conducts one way, blocks the other.
   ⚠️ Forward drop ~0.7 V for silicon, ~0.3 V for Schottky,
   and the exponential I-V relation means the "0.7 V" is a
   convenient fiction that shifts with current
⚠️ THE TYPES AND WHAT EACH IS FOR
   ⚠️ SIGNAL / RECTIFIER  power conversion, half and full wave
   ⚠️ SCHOTTKY  ⚠️ low forward drop, very fast recovery, higher
      leakage — used where switching speed or drop matters
   ⚠️ ZENER  ⚠️ deliberately operated in REVERSE BREAKDOWN as a
      voltage reference or clamp
   ⚠️ TVS  ⚠️ transient voltage suppression — the ESD protection
      part on every exposed line (see a peripherals reference §18)
   ⚠️ LED  forward-biased emission; ⚠️ needs current limiting,
      because the exponential I-V means a small voltage
      increase destroys it
   ⚠️ PHOTODIODE and solar cell — the same junction run backwards
   ⚠️ VARACTOR  voltage-controlled capacitance, used in tuning
⚠️ THE PRACTICAL USES THAT RECUR  ⚠️ FLYBACK/freewheeling diode
   across any inductive load (⚠️ a relay or motor without one
   destroys the driving transistor) · reverse polarity
   protection · ⚠️ diode-OR for redundant supplies · clamping ·
   level shifting
⚠️ ⚠️ DIODE LOGIC exists (AND/OR from diodes alone) but ⚠️ CANNOT
   INVERT and degrades the signal at every stage — which is
   exactly why active devices are necessary for real logic
```

---
