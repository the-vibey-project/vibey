---
id: skill-28-numbers-45f0df2400
purpose: 28 numbers
source: src/vibey_tools/skills/plugins/arm-architecture-deep-dive/skills/arm-reference/SKILL.md
requires: ["skill-27-misconceptions-3ef42f831c"]
links: ["skill-29-sources-ea6514bdf3"]
---

## §28. Numbers

```
⚠️ AArch64 registers  ⚠️ 31 GP + zero register (vs 16 on x86-64)
⚠️ Instruction length  ⚠️ fixed 32-bit (AArch64) · 16/32 (Thumb-2)
⚠️ Exception levels  EL0-EL3 · ⚠️ × security state (2, or 3 with CCA)
⚠️ Page granules  ⚠️ 4 KB / 16 KB / 64 KB
⚠️ NEON  fixed 128-bit
⚠️ SVE  ⚠️ 128-2048 bit, implementation-defined, VL-agnostic
⚠️ MTE tags  ⚠️ 4-bit → 1-in-16 random collision
⚠️ AAPCS64  ⚠️ X0-X7 args · X29 FP · X30 LR · 16-byte stack align
⚠️ ⚠️ ARM AGI CPU (Mar 2026)  ⚠️ 136 Neoverse V3 cores · 3.7 GHz ·
   TSMC 3nm · 300 W TDP · >8,000 cores/rack at 36 kW air-cooled ·
   >45,000 liquid-cooled (⚠️ Arm's claims)
⚠️ Neoverse deployed  ⚠️ >1 billion cores (Arm, Feb 2026)
⚠️ Graviton  ⚠️ >50% of AWS recent capacity · ~100k customers
⚠️ ⚠️ Arm server share  ⚠️ >45% REVENUE (IDC) vs 15-23% UNITS —
   ⚠️ not the same question
⚠️ CSS licences  ⚠️ 19 with 11 companies; 5 shipping (Arm)
⚠️ ARMv9 royalty  ⚠️ ~2× ARMv8 rate (reported)
```

---
