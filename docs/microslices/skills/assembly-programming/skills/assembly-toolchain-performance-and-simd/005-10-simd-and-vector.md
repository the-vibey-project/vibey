---
id: skill-10-simd-and-vector-47c839c4b7
purpose: 10 simd and vector
source: src/vibey_tools/skills/plugins/assembly-programming/skills/assembly-toolchain-performance-and-simd/SKILL.md
requires: ["skill-9-performance-9943efcadf"]
links: []
---

## §10. SIMD and Vector

### 10.1 The two models

**[DURABLE] There are now two fundamentally different vector programming models, and this
is the biggest conceptual split in modern assembly.**

**Fixed-width SIMD** — the register is a known size at compile time. SSE (128), AVX (256),
AVX-512 (512), NEON (128). You write a main loop plus a **scalar epilogue** for the
remainder, and you recompile (or runtime-dispatch) for each width.

**Scalable/vector-length-agnostic (VLA)** — the register size is unknown at compile time
and discovered at runtime. **ARM SVE/SVE2** and **RISC-V RVV** both work this way, deriving
from the Cray vector tradition rather than from packed SIMD. The same binary runs on
hardware with different vector lengths without recompiling.

```asm
; RISC-V RVV: the canonical strip-mined loop — no epilogue needed
loop:
    vsetvli t0, a0, e32, m8      ; "give me up to a0 elements of 32-bit, LMUL=8"
                                 ; t0 = how many you actually got
    vle32.v v0, (a1)             ; load t0 elements
    vadd.vi v0, v0, 1
    vse32.v v0, (a2)
    sub  a0, a0, t0              ; decrement remaining
    slli t1, t0, 2
    add  a1, a1, t1
    add  a2, a2, t1
    bnez a0, loop
```
**[DURABLE] `vsetvli` returning the granted length is the whole idea**: the hardware tells
you how much it can do, the loop handles any remainder naturally, and **the tail-handling
code that dominates fixed-width SIMD simply disappears.** SVE achieves the same with
predication and `whilelt`.

RVV specifics worth knowing: **32 vector registers**; **VLEN** (implementation vector
length) ranges from 128 to 16384 bits in shipping implementations; **SEW** (element width)
and **LMUL** (register grouping: 1/8 … 8) are set dynamically by `vsetvli`, so the *same*
instruction encoding works across element types and widths.

### 10.2 The x86 SIMD landscape

```
MMX(dead) → SSE→SSE4.2 (128-bit, xmm) → AVX/AVX2 (256-bit, ymm, 3-operand VEX)
  → AVX-512 (512-bit, zmm0–31, 8 mask registers k0–k7, EVEX encoding)
    → AVX10 (the convergence effort, §17)
```
**Mask registers (k0–k7) are AVX-512's best feature** and are underappreciated: per-lane
predication with zeroing or merging, which makes tail handling and conditional lanes far
cleaner than the blend-based tricks required in AVX2.

> **⚠️ GOTCHA — AVX-512 fragmentation is the reason AVX10 exists.** Intel shipped AVX-512
> on some server parts, then **disabled it on hybrid consumer parts** because the E-cores
> didn't have it. AMD implemented it (double-pumped on Zen 4, full-width on Zen 5). Result:
> a decade where you couldn't assume 512-bit vectors on a desktop x86 CPU. §17 → `assembly-reference` has the
> 2026 state.

> **⚠️ GOTCHA — downclocking.** Heavy 512-bit AVX-512 use historically dropped clock
> frequency on Intel server parts, so a vectorized loop could slow the *rest* of the
> program down. Much improved on recent silicon, but **always measure whole-application
> throughput, not just the kernel.**

> **⚠️ GOTCHA — AVX/SSE transition penalties.** Mixing legacy SSE and VEX-encoded AVX
> without `vzeroupper` causes expensive state-transition stalls. **Emit `vzeroupper` before
> returning from AVX code to a caller that might use SSE.**

### 10.3 ARM SIMD

**NEON** (128-bit, v0–v31) is the universal baseline on AArch64 — always present, no
runtime check needed.

**SVE/SVE2** is scalable and predicated. **SME/SME2 (Scalable Matrix Extension)** adds
**ZA storage** and outer-product operations for matrix work, with `SMSTART`/`SMSTOP` to
enter and leave streaming mode.

**[VERSIONED]** Deployment as of 2026 is uneven and worth knowing precisely: **the Apple
M4 family was the first consumer-grade silicon to support both SVE2 and SME** (Apple's own
LLVM contribution specifies **Armv9.2-A** for M4 and confirms SME and SME2). Arm's
**Lumex** cores bring SME2 to Android; some competing custom cores shipped SME1 + SVE2
first. **Do not assume SVE2 or SME are present** — check `HWCAP`/`ID_AA64*` at runtime and
keep a NEON path.

### 10.4 Writing SIMD well

**[DURABLE, and this is the most important advice in the section] Use intrinsics, not
assembly, for SIMD.** You get the exact instructions you want *plus* register allocation,
scheduling, inlining, and constant folding for free. Hand-written SIMD assembly is
justified when you're fighting the register allocator on a large kernel, and rarely
otherwise.

The techniques: **Structure-of-Arrays** layout, alignment where it matters, handling the
tail (or using a VLA ISA and not needing to), **shuffles/permutes** as the hard part,
horizontal reductions (expensive — keep them out of the loop), and **runtime dispatch**
(check CPUID/HWCAP once, select a function pointer, and note that indirect call overhead
means you dispatch per *buffer*, not per element).
