---
id: skill-14-latches-and-flip-flops-cf61d674e2
purpose: 14 latches and flip flops
source: src/vibey_tools/skills/plugins/digital-logic-and-firmware-engineering/skills/logic-sequential-timing-metastability-cdc-and-hdl/SKILL.md
requires: []
links: ["skill-15-timing-and-metastability-ebeef6451d"]
---

## §14. ⚠️ Latches and Flip-Flops

```
⚠️ ⚠️ THE DISTINCTION PEOPLE GET WRONG
   ⚠️ LATCH  ⚠️ LEVEL-sensitive — transparent while enable is
      asserted. Data flows through
   ⚠️ FLIP-FLOP  ⚠️ EDGE-triggered — samples only at the clock
      edge
   ⚠️ "Latch" and "flip-flop" are used loosely in conversation
      and mean genuinely different things in design
⚠️ CONSTRUCTION  ⚠️ cross-coupled inverters for storage · SR
   latch · gated D latch · ⚠️ MASTER-SLAVE (two latches on
   opposite clock phases) = edge-triggered flip-flop
⚠️ ⚠️ INFERRED LATCHES ARE A CLASSIC HDL BUG  ⚠️ an incomplete
   if or case statement in combinational logic makes the
   synthesizer infer a LATCH to hold the unassigned value.
   ⚠️ Almost never intended, causes timing problems, and every
   linter warns about it — heed the warning
⚠️ RESET  ⚠️ synchronous vs asynchronous. ⚠️ Asynchronous reset
   ASSERTION is fine; ⚠️ asynchronous DE-assertion is the
   hazard, because it can violate recovery/removal time —
   hence reset synchronizers
⚠️ ENABLE  ⚠️ use a proper enabled flip-flop, ⚠️ NOT a gated
   clock hand-built from logic (§8's clock gating is done with
   dedicated cells for exactly this reason)
⚠️ REGISTERS, shift registers, counters (⚠️ binary vs GRAY —
   Gray changes one bit at a time, which matters for §17)
```

---
