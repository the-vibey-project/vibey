---
id: skill-1-what-arm-actually-names-b5dd568df7
purpose: 1 what arm actually names
source: src/vibey_tools/skills/plugins/arm-architecture-deep-dive/skills/arm-what-arm-is-licensing-families-and-isa-generations/SKILL.md
requires: ["skill-0-routing-d8fcf5b95d"]
links: ["skill-2-the-licensing-model-d02c74977b"]
---

## §1. What "ARM" Actually Names

```
⚠️ THE LAYERS, and conflating them causes most confusion
   ⚠️ THE ARCHITECTURE  ⚠️ a specification — ARMv8-A, ARMv9-A.
      ⚠️ Defines instructions, registers, exception model, memory
      model. ⚠️ This is what "ARM" properly names
   ⚠️ THE MICROARCHITECTURE  ⚠️ an implementation — Cortex-X925,
      Neoverse V3, Apple's cores. ⚠️ Same contract, radically
      different execution
   ⚠️ THE PRODUCT  a chip integrating cores with everything else
⚠️ ⚠️ THEREFORE "ARM IS EFFICIENT" IS A CATEGORY ERROR. ⚠️ A
   Cortex-M0 and an Apple performance core share an ISA family
   and essentially nothing else. ⚠️ Efficiency is a property of
   implementations, targets and process nodes — see a
   microarchitecture reference §20, where the conclusion is that
   the ISA was never the barrier
⚠️ THE PROFILES  ⚠️ A (Application — MMU, rich OS) · R (Real-time
   — MPU, determinism) · ⚠️ M (Microcontroller — small, fast
   interrupts, §21)
⚠️ ARCHITECTURAL COMPLIANCE  ⚠️ Arm certifies that an
   implementation matches the spec, which is what makes the
   ecosystem work across dozens of vendors
```

---

# PART I — THE MODEL
