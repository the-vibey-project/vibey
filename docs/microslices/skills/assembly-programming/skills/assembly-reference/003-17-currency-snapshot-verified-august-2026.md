---
id: skill-17-currency-snapshot-verified-august-2026-ae617ba534
purpose: 17 currency snapshot verified august 2026
source: src/vibey_tools/skills/plugins/assembly-programming/skills/assembly-reference/SKILL.md
requires: ["skill-16-contested-questions-45d015266e"]
links: ["skill-18-the-canon-92b270feaa"]
---

## §17. Currency Snapshot — verified August 2026

| Thing | Status as of Aug 2026 | Decay risk |
|---|---|---|
| **Intel APX** | Doubles GPRs to **32**, adds a **unique destination register** for integer instructions (i.e. non-destructive three-operand x86), and extends predication. Intel reports **~10% fewer loads and ~20% fewer stores** in compiled code. Described as the most significant x86 ISA update since the move to 64 bits | Medium |
| **AVX10** | The convergence effort to clean up AVX-512: one ISA across P-cores and E-cores, with mask registers and 256-bit as the common denominator. **From AVX10.2 spec rev 4.0, Intel declared AVX10/512 will be used across all product lines, supporting 128/256/512 in all lines** — dropping the earlier AVX10/256-only plan (LLVM/Clang 22 correspondingly dropped the 256-bit-only options) | Medium |
| **Nova Lake** | ⚠️ Intel's **Instruction Set Extensions and Future Features manual rev 060 (November 2025)** confirms Nova Lake supports **AVX10.1, AVX10.2, APX**, plus SM4 (EVEX), MOVRS and PREFETCHRST2 — ending months of rumours it would ship without them. Launching as Core Ultra 400, **second half of 2026** | **High** |
| **RISC-V RVA23** | **Ratified 21 October 2024.** ⚠️ **The V (vector) extension is now MANDATORY** (optional in RVA22). Also newly mandatory: Zvfhmin, Zvbb, **Zvkt**, Zihintntl, Zicond, Zimop, Zcmop, Zcb, Zfa, Supm. **Baseline for the Android RISC-V ABI.** Scalar crypto Zkn/Zks **removed as options** — the goal is to move the ecosystem to vector crypto. Ratified specs are frozen and never revised | Low |
| **RVV** | v1.0 ratified 2021. VLA model; 32 vector registers; shipping **VLEN from 128 to 16384 bits**; SEW and LMUL set dynamically by `vsetvli` | Low |
| **Arm SVE2 / SME** | SVE2 mandatory in Armv9-A. **SME was added to the Arm ARM for A-profile on 20 March 2024.** ⚠️ **Apple M4 was the first consumer-grade silicon supporting both SVE2 and SME** (Apple's LLVM contribution specifies **Armv9.2-A** for M4 and confirms SME and SME2). Arm's **Lumex** cores bring SME2 to Android; some custom cores shipped SME1+SVE2 first. **Deployment remains uneven — runtime-detect** | **High** |
| **Intel DOIT** | Constant-time guarantees held **by default only before Ice Lake (Core) and Gracemont (Atom)**. On those and later they must be **explicitly enabled** via `IA32_UARCH_MISC_CTL` bit 0. **Intel does not recommend enabling globally.** **Kernel-only (MSR).** Explicitly covers data-dependent prefetchers | Medium |
| **Arm DIT** | `PSTATE.DIT`, Armv8.4+. **Unprivileged and cheap to set** from user space. Linux enabled it for arm64 in **v6.2 — kernel only**; user space must opt in. ⚠️ Guarantee is scoped to the registers an instruction explicitly uses, and makes **no statement about DMPs** | Medium |
| **RISC-V constant-time** | **Zkt** (scalar) and **Zvkt** (vector) attest data-independent execution latency for their instruction subsets. **Zvkt is mandatory in RVA23** — arguably the cleanest of the three vendors' approaches | Low |
| **LLVM constant-time intrinsics** | In development as of late 2025; lowers to `CSEL` on AArch64, masked arithmetic elsewhere. Rust Crypto, BearSSL, and PuTTY maintainers interested in **replacing inline-assembly workarounds** | **High** |

**Goes stale fastest:** Nova Lake / APX / AVX10 shipping status; SME deployment across
vendors; LLVM constant-time intrinsics. **Essentially never stale:** §1 → `assembly-fundamentals-and-isas` (machine model),
§6 → `assembly-toolchain-performance-and-simd` (ABIs), §8 → `assembly-toolchain-performance-and-simd` (reading disassembly), §9 → `assembly-toolchain-performance-and-simd` (performance fundamentals), §12.1 → `assembly-systems-crypto-and-inline` (the three
constant-time rules), §15 (anti-patterns).

---
