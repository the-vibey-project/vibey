---
id: skill-7-other-logic-families-2091a99b66
purpose: 7 other logic families
source: src/vibey_tools/skills/plugins/digital-logic-and-firmware-engineering/skills/logic-devices-transistors-cmos-gates-and-power/SKILL.md
requires: ["skill-6-sizing-and-drive-strength-36127acc66"]
links: ["skill-8-power-in-cmos-7175d37001"]
---

## §7. Other Logic Families

```
⚠️ PASS TRANSISTOR LOGIC  ⚠️ fewer transistors, and ⚠️ suffers
   the threshold drop of §3 — an nMOS pass gate delivers only
   VDD − Vt. ⚠️ Needs level restoration
⚠️ ⚠️ TRANSMISSION GATE  ⚠️ nMOS and pMOS in PARALLEL, gates
   driven oppositely — ⚠️ passes BOTH levels strongly. ⚠️ The
   standard building block for multiplexers and latches (§14)
⚠️ DYNAMIC / DOMINO LOGIC  ⚠️ precharge then evaluate, using a
   clock. ⚠️ Faster and smaller; ⚠️ vulnerable to charge sharing,
   leakage and noise, needs careful clocking, and is much less
   used than it once was because leakage got worse with scaling
⚠️ LEGACY FAMILIES worth recognizing  ⚠️ TTL (bipolar, fast for
   its day, power-hungry) · ⚠️ ECL (very fast, never off,
   enormous power) · ⚠️ 74-series and 4000-series CMOS, still
   genuinely useful for learning and glue logic
⚠️ ⚠️ LOGIC LEVELS AND INTERFACING  ⚠️ VIL/VIH/VOL/VOH and NOISE
   MARGIN. ⚠️ 3.3 V and 5 V and 1.8 V parts do not simply
   interconnect — ⚠️ level shifting is required, and driving a
   5 V-tolerant-only input from 3.3 V may not reach VIH
⚠️ OPEN DRAIN / OPEN COLLECTOR  ⚠️ needs a pull-up, gives
   wired-AND, and is why I²C works as a multi-drop bus
```

---
