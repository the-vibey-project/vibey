---
id: skill-5-execution-units-and-simd-4e3db0260d
purpose: 5 execution units and simd
source: src/vibey_tools/skills/plugins/microarchitecture-and-memory-systems/skills/uarch-pipelining-out-of-order-branch-prediction-and-simd/SKILL.md
requires: ["skill-4-branch-prediction-91d71e6dc6"]
links: []
---

## §5. Execution Units and SIMD

**⚠️ Superscalar width** — ⚠️ **the number of instructions issued per cycle, and the
practical limit is not the units but the RENAME and SCHEDULER width plus available ILP.**
**⚠️ Functional unit mix and latencies** — ⚠️ **integer ALU 1 cycle, multiply 3–5, FP add
and multiply 3–5, divide and square root far longer and often not pipelined.**
**⚠️ FMA (fused multiply-add)** — ⚠️ **one rounding instead of two, so it is both faster AND
more accurate; ⚠️ note it can change results versus separate operations, which matters for
reproducibility.**
**⚠️ SIMD** (AVX-512, NEON, SVE, RVV): ⚠️ **wide registers operating element-wise.**
⚠️ **The practical obstacles are ALIGNMENT, the need for contiguous data, tail handling,
and — for the widest units — DOWNCLOCKING under heavy vector load on some
implementations, which can make a vectorized kernel slow down neighbouring code.**
**⚠️ Predication and masking** let SIMD handle conditionals without branching, ⚠️ **and
scalable vector ISAs (SVE, RVV) express length-agnostic code so binaries survive width
changes.**
