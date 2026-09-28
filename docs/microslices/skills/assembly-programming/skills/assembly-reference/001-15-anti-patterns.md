---
id: skill-15-anti-patterns-d7d96fdbe5
purpose: 15 anti patterns
source: src/vibey_tools/skills/plugins/assembly-programming/skills/assembly-reference/SKILL.md
requires: []
links: ["skill-16-contested-questions-45d015266e"]
---

## §15. Anti-Patterns

| Anti-pattern | Why | Instead |
|---|---|---|
| Writing assembly before profiling | You'll optimize code that doesn't matter | Profile; then §0.1 → `assembly-fundamentals-and-isas`'s ladder |
| Hand-written asm where intrinsics would do | You give up register allocation, scheduling, inlining | Intrinsics (§13.1 → `assembly-systems-crypto-and-inline`) |
| Optimizing instruction count | Cache misses and mispredicts dominate by 100× | Optimize the dependency chain and memory (§9.1 → `assembly-toolchain-performance-and-simd`) |
| Clobbering a callee-saved register | Corruption surfaces in the caller, arbitrarily later | Know the ABI (§6 → `assembly-toolchain-performance-and-simd`); test with poison values (§14 → `assembly-systems-crypto-and-inline`) |
| Misaligning the stack | Faults inside unrelated library code | 16-byte alignment at every call |
| Assuming System V on Windows | Different arg registers, shadow space, xmm6–15 saved | Per-platform code paths |
| Assuming AArch64 saves all of v8–v15 | **Only the low 64 bits are callee-saved** | Save the full registers yourself |
| Using the red zone in kernel/interrupt code | It doesn't exist there | `-mno-red-zone`, explicit stack |
| Omitting CFI directives | No backtraces, broken unwinding, misattributed profiles | `.cfi_*` on every function (§7.2 → `assembly-toolchain-performance-and-simd`) |
| Writing to `ax`/`al` instead of `eax` | Partial-register merge stall | 32-bit ops zero-extend for free (§2.1 → `assembly-fundamentals-and-isas`) |
| `loop`, or branch-hint prefixes on x86 | Slower / ignored for two decades | `dec`/`jnz`; nothing |
| Reusing one accumulator in a reduction | Serializes on latency | Multiple accumulators (§9.2 → `assembly-toolchain-performance-and-simd`) |
| Forgetting `vzeroupper` | AVX↔SSE transition penalties | Emit it before returning |
| Assuming AVX-512 / SVE2 / SME are present | Wildly uneven deployment | Runtime dispatch via CPUID/HWCAP |
| Porting concurrent code from x86 without adding barriers | TSO hid the missing barrier; ARM/RISC-V won't | Understand the memory model (§1.4 → `assembly-fundamentals-and-isas`) |
| JIT: writing bytes without I-cache invalidation | Works on x86 (coherent I-cache), breaks on ARM/RISC-V | `dc cvau`/`ic ivau`/`isb`, or `fence.i` (§11 → `assembly-systems-crypto-and-inline`) |
| Inline asm without `"memory"`/`"cc"`/`&`/`volatile` | Works at `-O0`, fails at `-O2` | Get the clobbers right (§13.2 → `assembly-systems-crypto-and-inline`) |
| Branching or table-indexing on secret data | Timing side channel | Constant-time discipline (§12 → `assembly-systems-crypto-and-inline`) |
| Assuming constant-time arithmetic by default on modern Intel | **Not guaranteed by default on Ice Lake / Gracemont and later** | Understand DOIT/DIT/Zkt (§12.2 → `assembly-systems-crypto-and-inline`) |
| Optimizing from a 20-year-old guide | Half of it was Pentium 4 lore | Agner Fog / uops.info, and measure |
| No differential test against a C reference | Assembly bugs are subtle and data-dependent | Random differential testing (§14 → `assembly-systems-crypto-and-inline`) |
| Hand-writing crypto assembly with no verification story | The stakes are maximal and the failure is silent | Jasmin / HACL\* / fiat-crypto (§12.3 → `assembly-systems-crypto-and-inline`) |

---
