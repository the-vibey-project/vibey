---
id: skill-4-isa-generations-f87ab89edf
purpose: 4 isa generations
source: src/vibey_tools/skills/plugins/arm-architecture-deep-dive/skills/arm-what-arm-is-licensing-families-and-isa-generations/SKILL.md
requires: ["skill-3-product-families-ae81221de2"]
links: []
---

## §4. ISA Generations

```
⚠️ THE HISTORY THAT STILL MATTERS
   ⚠️ ARMv7-A  32-bit, ⚠️ Thumb-2 (mixed 16/32-bit encoding for
      code density — ⚠️ a genuine advantage in embedded)
   ⚠️ ⚠️ ARMv8-A (2011)  ⚠️ THE BIG BREAK. Introduced AArch64 —
      ⚠️ a NEW 64-bit instruction set, not an extension of the
      32-bit one. ⚠️ AArch32 retained for compatibility
   ⚠️ ARMv8.1 through 8.9  ⚠️ incremental: LSE atomics, RCpc,
      pointer authentication, MTE, BTI — ⚠️ note that many
      "ARMv8" features people rely on arrived in these dot
      releases and are OPTIONAL
   ⚠️ ⚠️ ARMv9-A (2021)  ⚠️ SVE2 mandatory, ⚠️ CCA/Realms,
      enhanced MTE, and a marketing reset. ⚠️ Built ON ARMv8.5
      rather than replacing it
   ⚠️ ARMv9.x continues the dot-release cadence
⚠️ ⚠️ 32-BIT SUPPORT IS BEING DROPPED. ⚠️ Modern application
   cores are increasingly AArch64-only, Android has moved to
   64-bit-only requirements, and Apple dropped 32-bit years ago.
   ⚠️ AArch32 is legacy
⚠️ ⚠️ FEATURE DISCOVERY  ⚠️ ID registers (and HWCAP via the OS)
   tell you what the implementation supports. ⚠️ You CANNOT
   assume a feature from the architecture version — this is the
   practical consequence of everything being optional
```
