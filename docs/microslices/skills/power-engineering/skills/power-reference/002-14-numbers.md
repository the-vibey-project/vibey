---
id: skill-14-numbers-ff99caf5fd
purpose: 14 numbers
source: src/vibey_tools/skills/plugins/power-engineering/skills/power-reference/SKILL.md
requires: ["skill-13-anti-patterns-5ac6b1afb4"]
links: ["skill-15-what-actually-moved-verified-august-2026-5fd9c36f8a"]
---

## §14. Numbers

```
FREQUENCY   60 Hz (NA, parts of Asia/LatAm) · 50 Hz (most of the world)
⚠️ Normal band ±0.05 Hz typical; under-frequency load shedding begins ~59.3 Hz (60 Hz sys)
Governor droop 4–5%

VOLTAGE LEVELS
Transmission 115 / 138 / 230 / 345 / 500 / 765 kV
Distribution 4.16 / 12.47 / 13.8 / 34.5 kV
Utilization 120/240 V (NA residential) · 208Y/120 · 480Y/277 V (NA commercial)
230 V / 400Y/230 V (most of the world)

THREE-PHASE
Wye: V_line = √3 V_phase · Delta: I_line = √3 I_phase
P_3φ = √3 · V_L · I_L · cos θ

POWER FACTOR
PF 0.7 draws ~43% more current than PF 1.0 for the same real power

PROTECTION (ANSI)
50/51 overcurrent · 87 differential · 21 distance · 27/59 volt · 81 freq · 79 reclose
⚠️ IEC 61850 GOOSE delivery requirement ~4 ms
⚠️ Inverter fault current ~1.1–2× rated (vs many× for synchronous machines)

DATACENTER
PUE: 1.0 ideal · ~1.1 hyperscale · 1.5–2.0 older enterprise
⚠️ AI rack density to ~140 kW (vs 5–15 kW traditional)
AI site draw 100–750 MW  ·  ⚠️ a 500 MW site at 90% util ≈ 3.9 TWh/yr
```

---
