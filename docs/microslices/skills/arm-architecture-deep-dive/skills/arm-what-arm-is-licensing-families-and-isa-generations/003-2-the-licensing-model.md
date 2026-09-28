---
id: skill-2-the-licensing-model-d02c74977b
purpose: 2 the licensing model
source: src/vibey_tools/skills/plugins/arm-architecture-deep-dive/skills/arm-what-arm-is-licensing-families-and-isa-generations/SKILL.md
requires: ["skill-1-what-arm-actually-names-b5dd568df7"]
links: ["skill-3-product-families-ae81221de2"]
---

## §2. ⚠️ The Licensing Model

```
⚠️ ⚠️ ARM DESIGNS AND LICENSES; IT HISTORICALLY DID NOT
   MANUFACTURE — ⚠️ and as of March 2026 that is no longer
   entirely true (§26.1)
⚠️ THE LICENCE TYPES
   ⚠️ CORE / IMPLEMENTATION LICENCE  ⚠️ use Arm's designed cores
      (Cortex, Neoverse). ⚠️ Most licensees
   ⚠️ ⚠️ ARCHITECTURE LICENCE  ⚠️ design your OWN core
      implementing the ISA. ⚠️ Rare, expensive, and the reason
      Apple, Qualcomm's Oryon and Amazon's designs can differ so
      much while running the same binaries
   ⚠️ ⚠️ CSS (Compute Subsystems)  ⚠️ pre-integrated, validated
      multi-IP blueprints rather than a bare core (§26.1)
⚠️ THE REVENUE STRUCTURE  ⚠️ UPFRONT LICENCE FEE + ⚠️ PER-CHIP
   ROYALTY. ⚠️ The royalty model means Arm's revenue tracks unit
   volume across the whole industry, which is why it appears in
   an enormous number of devices at very low revenue per device
⚠️ ⚠️ THE ARCHITECTURAL CONSEQUENCE  ⚠️ because licensees are
   competitors implementing one contract, the SPEC must be
   precise, extensions must be OPTIONAL and discoverable, and
   compliance must be testable. ⚠️ Compare RISC-V, where
   fragmentation is the standing concern (§25)
⚠️ SOFTBANK ownership, the failed NVIDIA acquisition, and the
   2023 IPO are the corporate context
```

---
