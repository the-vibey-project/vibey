---
id: skill-10-vector-extensions-b317a92a3c
purpose: 10 vector extensions
source: src/vibey_tools/skills/plugins/arm-architecture-deep-dive/skills/arm-vectors-atomics-numerics-and-security-architecture/SKILL.md
requires: []
links: ["skill-11-atomics-and-synchronization-e0d96328c9"]
---

## §10. ⚠️ Vector Extensions

```
⚠️ NEON (Advanced SIMD)  ⚠️ fixed 128-bit registers, widely
   supported, mandatory on most application cores. ⚠️ The safe
   baseline
⚠️ ⚠️ SVE (Scalable Vector Extension)  ⚠️ THE INTERESTING IDEA:
   ⚠️ VECTOR LENGTH AGNOSTIC. ⚠️ The register width is
   implementation-defined between 128 and 2048 bits, and
   ⚠️ THE SAME BINARY RUNS CORRECTLY ON ANY WIDTH
   ⚠️ HOW: ⚠️ predicate registers plus a loop idiom
   (WHILELT and INCB) that adapts to the hardware width at
   runtime. ⚠️ No re-compilation, no width-specific code paths,
   ⚠️ AND NO TAIL LOOP — predication handles the remainder
   ⚠️ COMPARE x86's approach of a new instruction set per width
   (SSE → AVX → AVX-512), each needing separate code paths
⚠️ SVE2  ⚠️ extends SVE to general-purpose and DSP-style
   workloads rather than just HPC. ⚠️ MANDATORY in ARMv9-A,
   which is what makes it targetable
⚠️ ⚠️ SME (Scalable Matrix Extension)  ⚠️ outer-product and
   matrix operations with a dedicated ZA tile storage array,
   plus ⚠️ STREAMING SVE MODE — a distinct processor mode with
   its own vector length. ⚠️ Aimed squarely at the ML workloads
   in a microarchitecture reference §13
⚠️ ⚠️ THE PRACTICAL CAVEAT  ⚠️ SVE's elegance is real and
   adoption has been gradual; ⚠️ NEON remains the compatibility
   baseline, and much shipping code still targets it. ⚠️ Check
   what your target actually implements (§4)
```

---
