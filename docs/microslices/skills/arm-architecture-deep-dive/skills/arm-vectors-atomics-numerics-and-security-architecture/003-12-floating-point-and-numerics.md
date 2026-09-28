---
id: skill-12-floating-point-and-numerics-99f75889ce
purpose: 12 floating point and numerics
source: src/vibey_tools/skills/plugins/arm-architecture-deep-dive/skills/arm-vectors-atomics-numerics-and-security-architecture/SKILL.md
requires: ["skill-11-atomics-and-synchronization-e0d96328c9"]
links: ["skill-13-trustzone-ffaeb2124b"]
---

## §12. Floating Point and Numerics

**⚠️ IEEE 754 compliance**, with FPCR and FPSR controlling rounding mode and reporting
exceptions.
**⚠️ Half precision (FP16)** as both a storage and an arithmetic format; ⚠️ **BF16 and
INT8 dot-product instructions (SDOT/UDOT) for ML** (see a microarchitecture reference §14).
**⚠️ FMA** as a single-rounding fused operation.
> **⚠️ GOTCHA — ARM's default flush-to-zero and denormal handling can differ from x86**,
> ⚠️ **and floating-point results can therefore differ in the last bits between
> architectures.** **⚠️ For anything requiring bit-exact reproducibility across platforms
> this is a real porting issue, and it surfaces in test suites that compare floating-point
> output exactly** (§23 → `arm-cortex-m-toolchain-porting-and-performance`).

---

# PART III — SECURITY ARCHITECTURE
