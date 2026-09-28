---
id: skill-19-quick-reference-216f2446b3
purpose: 19 quick reference
source: src/vibey_tools/skills/plugins/assembly-programming/skills/assembly-reference/SKILL.md
requires: ["skill-18-the-canon-92b270feaa"]
links: ["skill-20-sources-and-method-bacb2281b4"]
---

## §19. Quick Reference

### 19.1 Numbers to memorize
- **Cache line: 64 bytes.**
- Latency: **L1 ~4, L2 ~12, L3 ~40, DRAM ~200–300+ cycles.**
- Branch mispredict: **~15–20 cycles.**
- Integer divide: **20–100 cycles** (strength-reduce it).
- Stack alignment at a call: **16 bytes** on x86-64 SysV, AArch64, and RISC-V.
- x86-64 GPRs: **16** (32 with APX). AArch64: **31 + zero**. RISC-V: **32** (x0 = zero).
- x86 instruction length: **1–15 bytes.** AArch64 and RV: **fixed 32-bit** (RV `C`: 16).
- System V red zone: **128 bytes**. Windows shadow space: **32 bytes**.

### 19.2 First moves
| Task | Do this |
|---|---|
| Understand what the compiler did | **godbolt.org**, `-O2 -masm=intel` |
| Find the hot instruction | `perf record` → `perf annotate` |
| Look up latency/throughput | Agner Fog's tables; uops.info |
| Analyze a loop statically | `llvm-mca`, uiCA |
| Check ABI compliance | Poison callee-saved registers and verify after the call |
| Debug at instruction level | `gdb`: `layout asm`, `si`, `info registers` |
| Verify a hand-written routine | Random differential test vs. a C reference |
| Check for a CPU feature | CPUID (x86) / `getauxval(AT_HWCAP)` (Linux ARM/RV) |

### 19.3 Hand-written assembly review checklist
- [ ] Correct ABI: arg registers, return register, callee-saved preserved
- [ ] Stack 16-byte aligned at every call; no red-zone use in kernel/interrupt context
- [ ] CFI directives present, and `.type`/`.size` set
- [ ] Tail/remainder path tested (this is where SIMD bugs live)
- [ ] Unaligned and zero-length inputs tested
- [ ] Memory barriers correct for the *weakest* target, not just x86
- [ ] `vzeroupper` before returning from AVX code
- [ ] Runtime feature detection, with a fallback path
- [ ] For crypto: no secret-dependent branches, no secret-dependent addresses, no
      variable-latency ops on secrets — and a DIT/DOIT/Zkt story
- [ ] Differential-tested against a reference implementation
- [ ] Benchmarked on more than one microarchitecture

---
