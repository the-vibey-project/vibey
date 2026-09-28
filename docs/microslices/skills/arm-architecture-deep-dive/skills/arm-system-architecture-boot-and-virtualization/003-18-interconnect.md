---
id: skill-18-interconnect-57bd56eacf
purpose: 18 interconnect
source: src/vibey_tools/skills/plugins/arm-architecture-deep-dive/skills/arm-system-architecture-boot-and-virtualization/SKILL.md
requires: ["skill-17-interrupts-and-timers-031b369577"]
links: ["skill-19-boot-and-firmware-on-arm-5425cd273b"]
---

## §18. Interconnect

**⚠️ AMBA** is the family of bus specifications, ⚠️ **and it is as much a part of ARM's
ecosystem lock-in as the ISA — third-party IP is built to talk AMBA.**
⚠️ **AXI (high performance, channel-based, out-of-order), AHB and APB (simple, peripheral),
⚠️ ACE (adds cache coherency), and ⚠️ CHI (Coherent Hub Interface — the scalable
mesh-oriented protocol used in Neoverse-class designs).**
**⚠️ Coherent Mesh Networks** scale to very high core counts, ⚠️ **and interconnect design
is a large share of why two chips using the same cores perform differently.**
**⚠️ External coherency**: ⚠️ **CCIX historically, and now CXL** (see a microarchitecture
reference §17).
**⚠️ SMMU/IOMMU** for device address translation and DMA protection (§20).

---
