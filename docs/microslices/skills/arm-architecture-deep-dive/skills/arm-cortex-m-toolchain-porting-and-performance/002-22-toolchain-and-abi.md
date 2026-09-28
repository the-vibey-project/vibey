---
id: skill-22-toolchain-and-abi-8e84e15fb5
purpose: 22 toolchain and abi
source: src/vibey_tools/skills/plugins/arm-architecture-deep-dive/skills/arm-cortex-m-toolchain-porting-and-performance/SKILL.md
requires: ["skill-21-cortex-m-and-embedded-9715330020"]
links: ["skill-23-porting-from-x86-2324db594c"]
---

## §22. Toolchain and ABI

**⚠️ The AAPCS64 calling convention**: ⚠️ **X0–X7 for arguments and return, X8 for indirect
result, X9–X15 caller-saved, X19–X28 callee-saved, X29 frame pointer, X30 link register.**
**⚠️ The LINK REGISTER is the key difference from x86** — ⚠️ **a call puts the return address
in X30 rather than pushing it, so LEAF FUNCTIONS need not touch the stack at all.** ⚠️ **It
also means the return address is in a register where PAC can sign it** (§14 → `arm-vectors-atomics-numerics-and-security-architecture`).
**⚠️ Stack alignment to 16 bytes**, ⚠️ **and it is enforced — misalignment faults rather than
degrading.**
**⚠️ Compilers**: ⚠️ **GCC, LLVM/Clang and Arm's own toolchain; ⚠️ `-mcpu` and `-march`
selection matters more than on x86 because of feature optionality (§4 → `arm-what-arm-is-licensing-families-and-isa-generations`, §11 → `arm-vectors-atomics-numerics-and-security-architecture`).**
**⚠️ Debug**: ⚠️ **CoreSight for trace, ETM/ITM, gdb and OpenOCD, and SWD as the two-wire
debug interface on Cortex-M.**

---
