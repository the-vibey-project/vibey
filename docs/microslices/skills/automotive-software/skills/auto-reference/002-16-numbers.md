---
id: skill-16-numbers-58df2dbc77
purpose: 16 numbers
source: src/vibey_tools/skills/plugins/automotive-software/skills/auto-reference/SKILL.md
requires: ["skill-15-anti-patterns-d78f54fd1d"]
links: ["skill-17-what-actually-moved-051ec7bf0c"]
---

## §16. Numbers

```
BUSES
LIN 20 kbit/s · CAN 1 Mbit/s · CAN FD ~8 Mbit/s · FlexRay 10 Mbit/s
Automotive Ethernet 100 Mbit/s – multi-gig · ⚠️ CAN termination 2 × 120 Ω
CAN ID 11-bit standard / 29-bit extended · ⚠️ lower ID = higher priority
CAN payload 8 bytes · CAN FD 64 bytes · CAN XL 2048 bytes
⚠️ Target bus load <40–50%

SAFETY
ASIL A/B/C/D + QM · S0–S3 × E0–E4 × C0–C3 → ASIL
⚠️ ASIL D: SPFM ≥99%, LFM ≥90%, PMHF <10⁻⁸/h (10 FIT)
⚠️ ASIL B: SPFM ≥90%, LFM ≥60%, PMHF <10⁻⁷/h
MC/DC coverage required at ASIL D

REGULATION
⚠️ R155 Annex 5: 69 attack vectors · CSMS/SUMS certificates valid 3 years
54+ UNECE contracting parties

ENVIRONMENT
Operating −40 to +125 °C (⚠️ underhood higher) · 12 V nominal (⚠️ 9–16 V range)
48 V mild hybrid · 400/800 V traction
⚠️ Load dump transients to ~100 V+ · Design life 15 years / 240,000 km

SCALE
Legacy vehicle 70–150 ECUs · ⚠️ 100M+ lines of code cited for premium vehicles
Zonal target: >50% ECU reduction, ~40% wiring reduction
Harness: among the heaviest and costliest components, hand-assembled
```

---
