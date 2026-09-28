---
id: skill-9-mmu-and-translation-f9ba1ef00d
purpose: 9 mmu and translation
source: src/vibey_tools/skills/plugins/arm-architecture-deep-dive/skills/arm-aarch64-exception-levels-memory-model-and-mmu/SKILL.md
requires: ["skill-8-the-memory-model-c7464a05fc"]
links: []
---

## §9. MMU and Translation

**⚠️ Translation regimes** are per exception level and per security state, ⚠️ **which is why
there are so many system registers.**
**⚠️ TTBR0 and TTBR1** — ⚠️ **two base registers split by address range, so user and kernel
mappings live in separate tables and a context switch changes only TTBR0.** ⚠️ **This is
architecturally cleaner than the x86 arrangement and made Meltdown-style page-table
isolation cheaper.**
**⚠️ Granule sizes** of 4 KB, 16 KB and 64 KB — ⚠️ **note that 16 KB is what Apple uses, and
it is a real source of porting friction for code that assumes 4 KB pages.**
**⚠️ Multi-level tables, up to 4 or 5 levels**, ⚠️ **with configurable address size (TCR).**
**⚠️ ASIDs and VMIDs** avoid TLB flushes on context and VM switch.
**⚠️ STAGE 2 TRANSLATION** is the virtualization feature (§20 → `arm-system-architecture-boot-and-virtualization`): ⚠️ **the guest's "physical"
address is translated again by the hypervisor's tables — architected, not emulated.**
**⚠️ TLB maintenance** is explicit and has broadcast variants, ⚠️ **and TLBI instructions
plus the required DSB/ISB sequencing are a classic source of subtle kernel bugs.**
