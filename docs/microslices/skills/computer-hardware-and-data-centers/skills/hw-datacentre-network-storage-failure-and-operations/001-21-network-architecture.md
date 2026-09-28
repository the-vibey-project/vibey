---
id: skill-21-network-architecture-7cb7bea1e5
purpose: 21 network architecture
source: src/vibey_tools/skills/plugins/computer-hardware-and-data-centers/skills/hw-datacentre-network-storage-failure-and-operations/SKILL.md
requires: []
links: ["skill-22-storage-at-scale-bb237dc58a"]
---

## §21. Network Architecture

**⚠️ The topology shift**: ⚠️ **traditional three-tier (access/aggregation/core) was
designed for north-south traffic; ⚠️ modern LEAF-SPINE (Clos) topologies exist because
EAST-WEST traffic between servers now dominates.**
**⚠️ Oversubscription ratio** is the key design number — ⚠️ **how much aggregate access
bandwidth is contending for uplink capacity.**
**⚠️ For AI clusters specifically**: ⚠️ **collective operations (all-reduce) make the
network part of the compute path, so RDMA, lossless fabrics and congestion control matter
enormously; InfiniBand and increasingly Ethernet with RoCE; and ⚠️ RAIL-OPTIMIZED
topologies designed around GPU communication patterns.**
**⚠️ Optics**: ⚠️ **pluggable transceivers dominate, and CO-PACKAGED OPTICS is emerging to
cut the power cost of moving bits — networking power is a growing share of the total.**

---
