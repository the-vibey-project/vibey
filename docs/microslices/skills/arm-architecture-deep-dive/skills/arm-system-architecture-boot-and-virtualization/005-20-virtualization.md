---
id: skill-20-virtualization-cb041ab467
purpose: 20 virtualization
source: src/vibey_tools/skills/plugins/arm-architecture-deep-dive/skills/arm-system-architecture-boot-and-virtualization/SKILL.md
requires: ["skill-19-boot-and-firmware-on-arm-5425cd273b"]
links: []
---

## §20. Virtualization

**⚠️ EL2 is architected for it** (§7 → `arm-aarch64-exception-levels-memory-model-and-mmu`), ⚠️ **which is the structural advantage over x86's
retrofit.**
**⚠️ Stage 2 translation** (§9 → `arm-aarch64-exception-levels-memory-model-and-mmu`) gives guest-physical to host-physical translation in
hardware.
**⚠️ Trap and emulate** via HCR_EL2 bits — ⚠️ **the hypervisor chooses precisely which guest
operations trap.**
**⚠️ Virtual interrupts** through the GIC (§17), ⚠️ **and GICv4's direct injection removes
the hypervisor from the interrupt path entirely for many cases.**
**⚠️ VHE (Virtualization Host Extensions, ARMv8.1)** is the pragmatic addition: ⚠️ **it lets
a host kernel designed to run at EL1 run at EL2 with minimal changes, which is what made
KVM on ARM efficient rather than a split-mode compromise.**
**⚠️ SMMU** for device passthrough with DMA isolation.
**⚠️ Nested virtualization** is supported in later revisions and is much harder.
