---
id: skill-0-routing-6231e1d3de
purpose: 0 routing
source: src/vibey_tools/skills/plugins/assembly-programming/skills/assembly-fundamentals-and-isas/SKILL.md
requires: []
links: ["skill-1-the-machine-model-43bdcbc0f5"]
---

## §0. Routing

### 0.1 Should you write assembly at all?

**[DURABLE] For almost all code, no.** Modern compilers beat hand-written assembly on
anything but small, carefully-chosen kernels — and they retarget for free. The legitimate
reasons, in rough order of how often they're actually valid:

| Reason | Notes |
|---|---|
| **Reading compiler output** | The dominant use. Not writing at all |
| **Debugging optimized code / crash dumps** | You have no choice; the source is a fiction at `-O2` |
| **Reverse engineering, malware analysis, security research** | Reading, again |
| **Instructions the compiler won't emit** | Crypto (AES-NI, SHA, carry-less multiply), CRC, special atomics, cache control, hardware-specific instructions |
| **Constant-time cryptography** | §12 → `assembly-systems-crypto-and-inline` — the compiler is actively hostile to your requirements here |
| **Boot code, context switches, interrupt vectors, syscall stubs** | §11 → `assembly-systems-crypto-and-inline` — there is no C for "set up the stack before there is a stack" |
| **Hot kernels after profiling and after intrinsics** | Codecs, BLAS, hashing, parsers. And use **intrinsics first** |
| **Extremely constrained targets** | Tiny MCUs, boot ROMs, size-limited firmware |
| **Compiler bugs / missing optimizations** | Real, but verify before assuming |
| **Learning how machines work** | The best reason of all, and it doesn't need to ship |

**[DURABLE] The ladder, and take it in order:**
```
1. Better algorithm                      ← usually the whole answer
2. Better data layout / memory access    ← usually the rest of it
3. Compiler flags, PGO, LTO
4. Restructure C/C++/Rust so the compiler can vectorize
5. Compiler INTRINSICS                   ← 95% of the benefit, register allocation for free
6. Inline assembly for a specific instruction
7. Hand-written assembly functions
8. Hand-written assembly with microarchitectural scheduling
```
**Steps 5 and 7 are separated by a large maintenance cliff.** Intrinsics keep the
compiler's register allocation, scheduling, and inlining; hand-written assembly does not.

### 0.2 The question router

| Asked about... | Go to |
|---|---|
| Machine model: registers, memory, flags, endianness | §1 |
| x86-64 specifically | §2 |
| AArch64 / ARM64 specifically | §3 |
| RISC-V specifically | §4 |
| Other ISAs (embedded, GPU, historical) | §5 |
| Calling conventions and ABIs | §6 → `assembly-toolchain-performance-and-simd` |
| Assemblers, syntax, toolchain, linking | §7 → `assembly-toolchain-performance-and-simd` |
| Reading disassembly and compiler output | §8 → `assembly-toolchain-performance-and-simd` |
| Performance: pipelines, latency, caches, branches | §9 → `assembly-toolchain-performance-and-simd` |
| SIMD and vector programming | §10 → `assembly-toolchain-performance-and-simd` |
| Systems assembly: interrupts, context switch, boot | §11 → `assembly-systems-crypto-and-inline` |
| Cryptographic and constant-time assembly | §12 → `assembly-systems-crypto-and-inline` |
| Inline assembly and intrinsics | §13 → `assembly-systems-crypto-and-inline` |
| Debugging, testing, verification | §14 → `assembly-systems-crypto-and-inline` |
| "Don't do this" | §15 → `assembly-reference` |
| "Which approach is better?" | §16 → `assembly-reference` (contested) |
| "Is this still current?" | §17 → `assembly-reference` |
| Books, manuals, people | §18 → `assembly-reference` |

---
