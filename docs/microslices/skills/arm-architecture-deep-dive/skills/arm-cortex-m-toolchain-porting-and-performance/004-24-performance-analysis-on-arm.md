---
id: skill-24-performance-analysis-on-arm-edf75b7381
purpose: 24 performance analysis on arm
source: src/vibey_tools/skills/plugins/arm-architecture-deep-dive/skills/arm-cortex-m-toolchain-porting-and-performance/SKILL.md
requires: ["skill-23-porting-from-x86-2324db594c"]
links: ["skill-25-the-competitive-landscape-3e37905449"]
---

## §24. Performance Analysis on ARM

**⚠️ PMU counters** exist and are architected, ⚠️ **though the specific events available vary
by implementation — check the core's technical reference manual, not a generic list.**
**⚠️ Tools**: ⚠️ **`perf` works, Arm Streamline and Arm Forge for deeper analysis, and
vendor tools for specific silicon.**
**⚠️ SPE (Statistical Profiling Extension)** — ⚠️ **hardware sampling with instruction-level
attribution including memory latency, which is genuinely better than software sampling for
finding memory stalls.**
**⚠️ The top-down method applies** (see a microarchitecture reference §22), ⚠️ **with
vendor-specific implementations.**
**⚠️ ARM-specific things to look for**: ⚠️ **atomics falling back to exclusive loops (§11 → `arm-vectors-atomics-numerics-and-security-architecture`);
big.LITTLE scheduling putting your thread on the wrong core (§16 → `arm-system-architecture-boot-and-virtualization`); missing SVE/NEON
vectorization; barrier overuse where acquire/release would do (§8 → `arm-aarch64-exception-levels-memory-model-and-mmu`); and cache maintenance
in hot paths.**

---
