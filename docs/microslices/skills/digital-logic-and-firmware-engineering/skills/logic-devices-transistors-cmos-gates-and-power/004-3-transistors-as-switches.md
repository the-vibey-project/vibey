---
id: skill-3-transistors-as-switches-30fe96797c
purpose: 3 transistors as switches
source: src/vibey_tools/skills/plugins/digital-logic-and-firmware-engineering/skills/logic-devices-transistors-cmos-gates-and-power/SKILL.md
requires: ["skill-2-diodes-4df2d0fa93"]
links: ["skill-4-mosfet-switching-behaviour-8ebb7e8ce9"]
---

## §3. Transistors as Switches

**⚠️ BJT versus MOSFET**, ⚠️ **and the distinction that matters for logic:**
```
⚠️ BJT  ⚠️ CURRENT-controlled. Base current sets collector
   current. ⚠️ Continuous base current means continuous power —
   which is why bipolar logic families (TTL, ECL) burn power
   even when idle
⚠️ MOSFET  ⚠️ VOLTAGE-controlled via an insulated gate.
   ⚠️ ESSENTIALLY NO DC GATE CURRENT. ⚠️ THIS IS THE PROPERTY
   THAT MADE CMOS WIN — a gate that draws no static current can
   be scaled to billions
⚠️ THE MODES  cutoff (off) · ⚠️ linear/triode (⚠️ acting as a
   resistor — this is the SWITCH-ON region for logic) ·
   saturation (⚠️ constant current — the AMPLIFIER region, which
   digital design mostly passes THROUGH rather than sits in)
⚠️ n-CHANNEL vs p-CHANNEL  ⚠️ nMOS conducts when gate is HIGH;
   pMOS conducts when gate is LOW. ⚠️ This complementary pair is
   the whole basis of §5
⚠️ ⚠️ nMOS PASSES A STRONG 0 AND A WEAK 1; pMOS PASSES A STRONG 1
   AND A WEAK 0. ⚠️ This asymmetry is not a detail — it dictates
   which network goes where in a CMOS gate, and it is why pass
   transistor logic needs care (§7)
```

---
