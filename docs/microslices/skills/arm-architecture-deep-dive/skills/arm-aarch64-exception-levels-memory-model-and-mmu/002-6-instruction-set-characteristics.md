---
id: skill-6-instruction-set-characteristics-7455ae0ad0
purpose: 6 instruction set characteristics
source: src/vibey_tools/skills/plugins/arm-architecture-deep-dive/skills/arm-aarch64-exception-levels-memory-model-and-mmu/SKILL.md
requires: ["skill-5-aarch64-5c0e340783"]
links: ["skill-7-exception-levels-901f596968"]
---

## §6. Instruction Set Characteristics

**⚠️ Load/store architecture** — ⚠️ **arithmetic operates on registers only, so memory
access is explicit; this makes the memory model (§8) analyzable.**
**⚠️ Load/store PAIR (LDP/STP)** — ⚠️ **two registers in one instruction, heavily used in
prologues and epilogues.**
**⚠️ CSEL and the conditional-select family** — ⚠️ **branchless selection without full
predication.**
**⚠️ Bitfield instructions** (UBFX, SBFX, BFI) — ⚠️ **single-instruction extract and insert,
notably better than the x86 equivalents.**
**⚠️ Encoding constraints**: ⚠️ **immediates are limited by the fixed 32-bit width, so large
constants need MOVZ/MOVK sequences or a literal pool — ⚠️ which is why disassembly shows
apparently redundant instruction pairs.**
**⚠️ System registers** are accessed via MRS/MSR, ⚠️ **and the naming convention
(`REG_ELx`) tells you which exception level owns it** (§7).
**⚠️ Code density**: ⚠️ **AArch64 is denser than fixed-32-bit RISC traditionally was but
less dense than Thumb-2 or x86 — a deliberate trade for decode simplicity.**

---
