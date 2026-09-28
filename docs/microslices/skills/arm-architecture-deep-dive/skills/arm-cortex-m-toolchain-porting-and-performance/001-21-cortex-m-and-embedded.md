---
id: skill-21-cortex-m-and-embedded-9715330020
purpose: 21 cortex m and embedded
source: src/vibey_tools/skills/plugins/arm-architecture-deep-dive/skills/arm-cortex-m-toolchain-porting-and-performance/SKILL.md
requires: []
links: ["skill-22-toolchain-and-abi-8e84e15fb5"]
---

## §21. ⚠️ Cortex-M and Embedded

> **⚠️ By unit volume this is the ARM most chips actually are, and it is a genuinely
> different architecture — not a small Cortex-A.**
```
⚠️ ⚠️ THUMB-2 ONLY. ⚠️ No AArch64, no ARM 32-bit encoding —
   ⚠️ a mixed 16/32-bit instruction set chosen for CODE DENSITY,
   which matters enormously when flash is the cost driver
⚠️ ⚠️ NO MMU. ⚠️ An optional MPU gives region-based protection
   without translation. ⚠️ This means no virtual memory, no
   fork(), and a flat physical address space
⚠️ ⚠️ THE INTERRUPT DESIGN IS THE STANDOUT FEATURE
   ⚠️ NVIC with ⚠️ AUTOMATIC REGISTER STACKING IN HARDWARE on
   exception entry — ⚠️ so an ISR can be a plain C function with
   no assembly wrapper
   ⚠️ ⚠️ TAIL-CHAINING  back-to-back interrupts skip the
   unstack/restack entirely
   ⚠️ Deterministic, low, documented interrupt latency —
   ⚠️ which is the whole point for real-time work
⚠️ ⚠️ EXC_RETURN  a magic value in LR on exception entry that
   encodes which stack and mode to return to — ⚠️ startling the
   first time you see it in a debugger
⚠️ THE FAMILY  ⚠️ M0/M0+ (smallest) · M3 · M4 (DSP) · M7
   (cache, higher performance) · ⚠️ M23/M33 (TrustZone-M) ·
   M55/M85 (⚠️ Helium/MVE — SIMD for ML at the edge)
⚠️ ⚠️ CMSIS  the standard HAL and register-definition layer,
   which is what makes vendor peripherals tractable
⚠️ MEMORY MAP is architecturally defined — ⚠️ code, SRAM,
   peripheral and system regions at fixed addresses, plus
   ⚠️ BIT-BANDING on some parts for atomic single-bit access
```

---

# PART V — WORKING WITH IT
