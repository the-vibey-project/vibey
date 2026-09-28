---
id: skill-13-trustzone-ffaeb2124b
purpose: 13 trustzone
source: src/vibey_tools/skills/plugins/arm-architecture-deep-dive/skills/arm-vectors-atomics-numerics-and-security-architecture/SKILL.md
requires: ["skill-12-floating-point-and-numerics-99f75889ce"]
links: ["skill-14-pointer-authentication-bti-and-mte-06b0de8b99"]
---

## §13. ⚠️ TrustZone

```
⚠️ ⚠️ THE IDEA  ⚠️ split the system into a SECURE WORLD and a
   NON-SECURE WORLD, with the split enforced in HARDWARE
   throughout — ⚠️ not just in the CPU, but propagated across
   the interconnect as an extra address bit (the NS bit), so
   peripherals and memory regions are partitioned too
⚠️ THE MONITOR at EL3 handles world switches via SMC calls
⚠️ WHAT RUNS IN THE SECURE WORLD  ⚠️ a Trusted Execution
   Environment — key storage, DRM, biometric matching, secure
   payment, mobile device attestation
⚠️ ⚠️ THE HONEST CRITIQUES
   ⚠️ TEE implementations are large, proprietary, and have had
      SERIOUS VULNERABILITIES — ⚠️ and a compromise there is
      more privileged than the kernel
   ⚠️ ⚠️ TrustZone protects against the NORMAL world, not
      against the secure world's own bugs or against physical
      attack
   ⚠️ ⚠️ IT IS ALSO A LOCK-DOWN MECHANISM. ⚠️ The same feature
      that protects your keys enforces DRM and can prevent the
      device owner from controlling their own hardware — the
      security benefit and the control question are inseparable
⚠️ CORTEX-M has TrustZone-M — ⚠️ a different, lighter design
   with fast state transitions rather than a monitor (§21)
```

---
