---
id: skill-5-static-cmos-gates-adb0daf92c
purpose: 5 static cmos gates
source: src/vibey_tools/skills/plugins/digital-logic-and-firmware-engineering/skills/logic-devices-transistors-cmos-gates-and-power/SKILL.md
requires: ["skill-4-mosfet-switching-behaviour-8ebb7e8ce9"]
links: ["skill-6-sizing-and-drive-strength-36127acc66"]
---

## §5. ⚠️ Static CMOS Gates

> **⚠️ The single most useful construction in this file. Once you see it, you can draw any
> logic gate from its Boolean expression mechanically.**
```
⚠️ THE STRUCTURE  ⚠️ every static CMOS gate is TWO NETWORKS
   ⚠️ PULL-UP NETWORK (PUN)  ⚠️ pMOS transistors, connects output
      to VDD
   ⚠️ PULL-DOWN NETWORK (PDN)  ⚠️ nMOS transistors, connects
      output to GND
   ⚠️ THEY ARE COMPLEMENTARY AND MUTUALLY EXCLUSIVE — exactly one
      conducts for any input combination. ⚠️ Both on = short
      circuit; both off = floating output
⚠️ ⚠️ THE CONSTRUCTION RULE
   ⚠️ PDN: SERIES nMOS = AND · PARALLEL nMOS = OR
   ⚠️ PUN: the DUAL — series becomes parallel and vice versa
   ⚠️ The output is INHERENTLY INVERTED
⚠️ ⚠️ THEREFORE NAND AND NOR ARE THE NATURAL GATES, and
   ⚠️ AND and OR are MORE EXPENSIVE than NAND and NOR because
   they are a NAND/NOR followed by an inverter. ⚠️ This is
   backwards from how people learn Boolean algebra, and it is
   why synthesized netlists are full of NANDs
⚠️ THE INVERTER  one pMOS, one nMOS, gates tied together —
   ⚠️ the simplest possible instance of the pattern
⚠️ ⚠️ NAND IS PREFERRED OVER NOR in practice, because NOR puts
   pMOS devices in SERIES — and pMOS is intrinsically weaker
   (lower hole mobility), so a series pMOS stack is slow (§6)
⚠️ COMPLEX GATES  ⚠️ AOI (and-or-invert) and OAI implement
   multi-level functions in ONE gate, which is faster and
   smaller than composing separate gates
⚠️ STACK HEIGHT  ⚠️ practically limited to about 3-4 series
   devices, because series resistance and body effect compound
```

---
