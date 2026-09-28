---
id: skill-17-interrupts-and-timers-031b369577
purpose: 17 interrupts and timers
source: src/vibey_tools/skills/plugins/arm-architecture-deep-dive/skills/arm-system-architecture-boot-and-virtualization/SKILL.md
requires: ["skill-16-big-little-and-dynamiq-8ac7aa694f"]
links: ["skill-18-interconnect-57bd56eacf"]
---

## §17. Interrupts and Timers

**⚠️ The GIC (Generic Interrupt Controller)** — ⚠️ **GICv2, v3 and v4, with v3+ using system
registers rather than MMIO for the CPU interface, which is substantially faster.**
**⚠️ Interrupt types**: ⚠️ **SPI (shared peripheral), PPI (private per-core), SGI
(software-generated, for inter-processor interrupts), and LPI (message-signalled, via the
ITS — which is how MSI-X scales on ARM servers).**
**⚠️ Affinity routing and priority**, ⚠️ **and GICv4's direct injection of virtual
interrupts into guests without hypervisor involvement** (§20).
**⚠️ The Generic Timer** is architected — ⚠️ **a system counter plus per-core comparators,
with virtual timer offsets for guests, which is why timekeeping on ARM VMs is cleaner than
the x86 history of TSC problems.**

---
