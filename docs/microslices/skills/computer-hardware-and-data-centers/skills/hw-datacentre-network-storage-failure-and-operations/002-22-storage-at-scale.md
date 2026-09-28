---
id: skill-22-storage-at-scale-bb237dc58a
purpose: 22 storage at scale
source: src/vibey_tools/skills/plugins/computer-hardware-and-data-centers/skills/hw-datacentre-network-storage-failure-and-operations/SKILL.md
requires: ["skill-21-network-architecture-7cb7bea1e5"]
links: ["skill-23-failure-at-scale-9aa5db441a"]
---

## §22. Storage at Scale

**⚠️ The tiers**: ⚠️ **NVMe for hot, SSD for warm, HDD for capacity, tape for archive
(⚠️ tape is very much alive for cost per terabyte and for offline ransomware resistance).**
**⚠️ Distributed storage**: ⚠️ **replication versus ERASURE CODING (⚠️ far better storage
efficiency for the same durability, at the cost of rebuild bandwidth and CPU).**
**⚠️ The CAP theorem** frames the fundamental trade in distributed systems, ⚠️ **and in
practice the choice is between consistency and availability during a partition.**
**⚠️ Durability claims** ("eleven nines") are ⚠️ **modelled figures about drive failure, and
they do not cover operator error, software bugs or correlated failures — which are the
things that actually destroy data** (§23).

---
