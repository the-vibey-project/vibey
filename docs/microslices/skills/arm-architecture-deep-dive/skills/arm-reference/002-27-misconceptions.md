---
id: skill-27-misconceptions-3ef42f831c
purpose: 27 misconceptions
source: src/vibey_tools/skills/plugins/arm-architecture-deep-dive/skills/arm-reference/SKILL.md
requires: ["skill-26-what-s-live-checked-august-2026-16a0f58733"]
links: ["skill-28-numbers-45f0df2400"]
---

## §27. Misconceptions

| Misconception | Correction |
|---|---|
| ARM is inherently more efficient than x86 | ⚠️ **Efficiency is an implementation property. The ISA isn't the barrier** (§1 → `arm-what-arm-is-licensing-families-and-isa-generations`, §25 → `arm-cortex-m-toolchain-porting-and-performance`) |
| "ARM performance" is a meaningful phrase | ⚠️ **Cortex-M0 and an Apple core share almost nothing** (§1 → `arm-what-arm-is-licensing-families-and-isa-generations`) |
| ARM is RISC and therefore simple | ⚠️ **AArch64 has ~1000 instructions. RISC/CISC is historical** (§6 → `arm-aarch64-exception-levels-memory-model-and-mmu`) |
| ARMv9 replaced ARMv8 | ⚠️ **It's built on ARMv8.5** (§4 → `arm-what-arm-is-licensing-families-and-isa-generations`) |
| Architecture version tells you the features | ⚠️ **Most are OPTIONAL. Check ID registers** (§4 → `arm-what-arm-is-licensing-families-and-isa-generations`) |
| AArch64 extends the 32-bit ISA | ⚠️ **It's a new instruction set. Different encoding** (§5 → `arm-aarch64-exception-levels-memory-model-and-mmu`) |
| ARM has conditional execution everywhere | ⚠️ **Dropped in AArch64. CSEL replaced it** (§5 → `arm-aarch64-exception-levels-memory-model-and-mmu`) |
| x86-correct concurrent code works on ARM | ⚠️ **Weak ordering. Silently broken, intermittently** (§8 → `arm-aarch64-exception-levels-memory-model-and-mmu`, §23 → `arm-cortex-m-toolchain-porting-and-performance`) |
| Use DMB for ordering | ⚠️ **LDAR/STLR are usually faster and clearer** (§8 → `arm-aarch64-exception-levels-memory-model-and-mmu`) |
| Atomics perform the same everywhere | ⚠️ **Without LSE you get exclusive retry loops** (§11 → `arm-vectors-atomics-numerics-and-security-architecture`) |
| A JIT works the same as on x86 | ⚠️ **I-cache and D-cache aren't coherent. Explicit maintenance** (§8 → `arm-aarch64-exception-levels-memory-model-and-mmu`, §23 → `arm-cortex-m-toolchain-porting-and-performance`) |
| Pages are 4 KB | ⚠️ **4/16/64 KB. Apple uses 16 KB** (§9 → `arm-aarch64-exception-levels-memory-model-and-mmu`) |
| SVE is just a wider NEON | ⚠️ **Vector-length agnostic — one binary, any width** (§10 → `arm-vectors-atomics-numerics-and-security-architecture`) |
| TrustZone makes a device secure | ⚠️ **TEEs have had serious vulnerabilities, and it's also a lock-down tool** (§13 → `arm-vectors-atomics-numerics-and-security-architecture`) |
| MTE catches every memory bug | ⚠️ **Probabilistic — 4-bit tags, 1-in-16 collisions** (§14 → `arm-vectors-atomics-numerics-and-security-architecture`) |
| Pointer authentication is unbreakable | ⚠️ **Signing gadgets and short MACs are real limits** (§14 → `arm-vectors-atomics-numerics-and-security-architecture`) |
| ARM boots like a PC | ⚠️ **No architectural BIOS. SystemReady certification is why servers do** (§19 → `arm-system-architecture-boot-and-virtualization`) |
| Cortex-M is a small Cortex-A | ⚠️ **Thumb-2 only, no MMU, hardware register stacking** (§21 → `arm-cortex-m-toolchain-porting-and-performance`) |
| ISRs need an assembly wrapper | ⚠️ **Not on Cortex-M. The NVIC stacks in hardware** (§21 → `arm-cortex-m-toolchain-porting-and-performance`) |
| char is signed | ⚠️ **Unsigned by default on ARM. Compiles silently** (§23 → `arm-cortex-m-toolchain-porting-and-performance`) |
| Porting is mostly recompiling | ⚠️ **True for app code; low-level code is where it bites** (§23 → `arm-cortex-m-toolchain-porting-and-performance`) |
| Arm only licenses IP | ⚠️ **It ships its own silicon as of March 2026** (§26.1) |
| Arm has 45% of the server market | ⚠️ **Of REVENUE. Units are 15-23%. Ask which** (§26.2) |
| Hyperscalers moved to Arm for speed | ⚠️ **Power, and freeing capacity for AI racks** (§26.2) |

---
