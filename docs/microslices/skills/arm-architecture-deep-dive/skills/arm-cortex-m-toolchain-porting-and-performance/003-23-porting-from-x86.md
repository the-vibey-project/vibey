---
id: skill-23-porting-from-x86-2324db594c
purpose: 23 porting from x86
source: src/vibey_tools/skills/plugins/arm-architecture-deep-dive/skills/arm-cortex-m-toolchain-porting-and-performance/SKILL.md
requires: ["skill-22-toolchain-and-abi-8e84e15fb5"]
links: ["skill-24-performance-analysis-on-arm-edf75b7381"]
---

## §23. ⚠️ Porting from x86

```
⚠️ ⚠️ IN ORDER OF HOW MUCH TROUBLE THEY CAUSE
   ⚠️ 1. MEMORY ORDERING (§8)  ⚠️ THE BIG ONE. ⚠️ Lock-free
      code, hand-rolled synchronization and anything using
      `volatile` as a synchronization primitive can be silently
      broken. ⚠️ Use the language's atomics; ⚠️ and TEST UNDER
      LOAD ON REAL ARM HARDWARE — the bugs are probabilistic
   ⚠️ 2. ⚠️ INTRINSICS AND INLINE ASSEMBLY  ⚠️ SSE/AVX intrinsics
      do not exist. ⚠️ Options: portable libraries, SIMDe-style
      translation headers, or NEON/SVE rewrites (§10)
   ⚠️ 3. ⚠️ char IS UNSIGNED BY DEFAULT ON ARM. ⚠️ Code assuming
      signed char has real behaviour differences, and it
      compiles silently
   ⚠️ 4. ⚠️ PAGE SIZE ASSUMPTIONS — ⚠️ 4 KB is not guaranteed
      (§9); Apple uses 16 KB
   ⚠️ 5. ⚠️ UNALIGNED ACCESS  ⚠️ generally supported on normal
      memory in AArch64, ⚠️ but NOT on device memory and not for
      exclusives — and this catches driver code
   ⚠️ 6. FLOATING POINT last-bit differences (§12)
   ⚠️ 7. ⚠️ SELF-MODIFYING CODE AND JITs  ⚠️ require explicit
      cache maintenance (§8), and this is a hard-crash-level bug
   ⚠️ 8. Build system, dependencies, and containers built for
      one architecture
⚠️ ⚠️ WHAT IS USUALLY EASY  ⚠️ ordinary application code in a
   memory-safe or well-behaved language recompiles and runs.
   ⚠️ The horror stories are concentrated in low-level code
⚠️ EMULATION  ⚠️ Rosetta 2 and Windows Prism translate x86
   binaries — ⚠️ and note the memory model problem AGAIN: Apple
   silicon implements an optional TSO MODE specifically so
   translated x86 code gets the ordering it assumes
```

---
