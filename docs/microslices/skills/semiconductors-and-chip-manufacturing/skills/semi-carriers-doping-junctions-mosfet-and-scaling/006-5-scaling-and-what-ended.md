---
id: skill-5-scaling-and-what-ended-507ff30d91
purpose: 5 scaling and what ended
source: src/vibey_tools/skills/plugins/semiconductors-and-chip-manufacturing/skills/semi-carriers-doping-junctions-mosfet-and-scaling/SKILL.md
requires: ["skill-4-the-mosfet-f091f95f35"]
links: []
---

## §5. ⚠️ Scaling, and What Ended

> **⚠️ The most misunderstood story in technology, and getting it right explains almost
> everything about the modern industry.**
```
⚠️ DENNARD SCALING (the real engine)  ⚠️ shrink dimensions AND
   voltage together, and power density stays CONSTANT while
   speed rises and cost per transistor falls.
   ⚠️ THIS IS WHAT DELIVERED "free" performance for decades
⚠️ ⚠️ DENNARD SCALING ENDED AROUND THE MID-2000s
   ⚠️ WHY: voltage could not keep falling, because Vt could not
   fall without leakage exploding — and it couldn't, because of
   the 60 mV/decade subthreshold floor (§4)
   ⚠️ CONSEQUENCE: power density rose. ⚠️ The response was
   MULTICORE — not because parallel was better, but because
   frequency scaling had stopped
⚠️ ⚠️ DARK SILICON  the fraction of a chip that cannot be powered
   simultaneously within the thermal budget. ⚠️ This is why modern
   chips are full of specialized accelerators used intermittently
⚠️ MOORE'S LAW  ⚠️ an ECONOMIC observation about transistors per
   chip at minimum cost, not a law of physics. ⚠️ Transistor
   density still increases; ⚠️ COST PER TRANSISTOR has largely
   stopped falling at the leading edge, which is the more
   important change
```
> **⚠️ GOTCHA — "3nm" IS A MARKETING NAME.** ⚠️ **Since roughly the 22nm generation, node
> names have not corresponded to any physical feature on the chip — not gate length, not
> half-pitch, not fin width.** **⚠️ Different foundries' same-numbered nodes have materially
> different densities and characteristics.**
> ⚠️ **The meaningful metrics are TRANSISTOR DENSITY (MTr/mm²), SRAM bitcell area, and
> power-performance-area at a given design.** **⚠️ Compare those, never the name.**
