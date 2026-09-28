---
id: skill-30-quick-reference-dc70ff65d0
purpose: 30 quick reference
source: src/vibey_tools/skills/plugins/arm-architecture-deep-dive/skills/arm-reference/SKILL.md
requires: ["skill-29-sources-ea6514bdf3"]
links: ["skill-31-method-4124361a26"]
---

## §30. Quick Reference

### 30.1 Picker
| Question | Where |
|---|---|
| Which ARM is this? | ⚠️ **Architecture, core, product — three questions** (§1 → `arm-what-arm-is-licensing-families-and-isa-generations`, §3 → `arm-what-arm-is-licensing-families-and-isa-generations`) |
| Can I use feature X? | ⚠️ **Check ID registers. Optional ≠ present** (§4 → `arm-what-arm-is-licensing-families-and-isa-generations`) |
| Why does my lock-free code fail? | ⚠️ **Weak memory ordering** (§8 → `arm-aarch64-exception-levels-memory-model-and-mmu`, §23 → `arm-cortex-m-toolchain-porting-and-performance`) |
| Which barrier do I need? | ⚠️ **Probably none — use LDAR/STLR** (§8 → `arm-aarch64-exception-levels-memory-model-and-mmu`) |
| Atomics are slow | ⚠️ **Check LSE is enabled in your build** (§11 → `arm-vectors-atomics-numerics-and-security-architecture`) |
| My JIT crashes | ⚠️ **Cache maintenance between I and D** (§8 → `arm-aarch64-exception-levels-memory-model-and-mmu`, §23 → `arm-cortex-m-toolchain-porting-and-performance`) |
| SVE or NEON? | ⚠️ **NEON for compatibility, SVE if the target has it** (§10 → `arm-vectors-atomics-numerics-and-security-architecture`) |
| How do I harden this? | ⚠️ **PAC + BTI + MTE, if silicon supports them** (§14 → `arm-vectors-atomics-numerics-and-security-architecture`) |
| Why won't this board boot a generic OS? | ⚠️ **No SystemReady certification** (§19 → `arm-system-architecture-boot-and-virtualization`) |
| Writing an ISR on Cortex-M | ⚠️ **Plain C function. Hardware stacks for you** (§21 → `arm-cortex-m-toolchain-porting-and-performance`) |
| Porting from x86 — what breaks? | ⚠️ **Memory ordering, intrinsics, char signedness** (§23 → `arm-cortex-m-toolchain-porting-and-performance`) |
| Is ARM taking over servers? | ⚠️ **Depends entirely on revenue vs units** (§26.2) |

### 30.2 Porting checklist
- [ ] ⚠️ **All synchronization uses language atomics, not `volatile`** (§8 → `arm-aarch64-exception-levels-memory-model-and-mmu`, §23 → `arm-cortex-m-toolchain-porting-and-performance`)
- [ ] ⚠️ **Lock-free code reviewed against the WEAK model** (§8 → `arm-aarch64-exception-levels-memory-model-and-mmu`)
- [ ] ⚠️ **Tested under load on real ARM hardware, not just emulation** (§23 → `arm-cortex-m-toolchain-porting-and-performance`)
- [ ] x86 intrinsics replaced or abstracted (§10 → `arm-vectors-atomics-numerics-and-security-architecture`, §23 → `arm-cortex-m-toolchain-porting-and-performance`)
- [ ] ⚠️ **`char` signedness assumptions found and fixed** (§23 → `arm-cortex-m-toolchain-porting-and-performance`)
- [ ] Page size not hardcoded to 4 KB (§9 → `arm-aarch64-exception-levels-memory-model-and-mmu`, §23 → `arm-cortex-m-toolchain-porting-and-performance`)
- [ ] ⚠️ **JIT or self-modifying code does cache maintenance** (§8 → `arm-aarch64-exception-levels-memory-model-and-mmu`)
- [ ] Unaligned access assumptions checked, especially in drivers (§23 → `arm-cortex-m-toolchain-porting-and-performance`)
- [ ] Floating-point exact-comparison tests reviewed (§12 → `arm-vectors-atomics-numerics-and-security-architecture`)
- [ ] ⚠️ **Build targets the right `-mcpu`/`-march` — LSE enabled** (§11 → `arm-vectors-atomics-numerics-and-security-architecture`, §22 → `arm-cortex-m-toolchain-porting-and-performance`)
- [ ] ⚠️ **Verified which optional features the target actually has** (§4 → `arm-what-arm-is-licensing-families-and-isa-generations`)
- [ ] Container images and dependencies available for arm64 (§23 → `arm-cortex-m-toolchain-porting-and-performance`)

---
