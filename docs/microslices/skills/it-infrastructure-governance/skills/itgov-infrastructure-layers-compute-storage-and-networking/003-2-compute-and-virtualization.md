---
id: skill-2-compute-and-virtualization-ebf237b364
purpose: 2 compute and virtualization
source: src/vibey_tools/skills/plugins/it-infrastructure-governance/skills/itgov-infrastructure-layers-compute-storage-and-networking/SKILL.md
requires: ["skill-1-the-layers-06964e8a32"]
links: ["skill-3-storage-6c9137c57a"]
---

## §2. Compute and Virtualization

**Bare metal** — ⚠️ **still correct for latency-sensitive, licence-bound, or
hardware-dependent workloads.**
**Hypervisors**: **Type 1 (bare metal — ESXi, Hyper-V, KVM, Xen)** vs **Type 2 (hosted)**.
**⚠️ Consolidation ratios, overcommit (memory and CPU), and the failure mode of
overcommitting: noisy neighbours and unpredictable latency.**
**Clustering and HA**: **live migration, failover, anti-affinity rules** (⚠️ **so your two
redundant VMs don't land on the same physical host — a classic and embarrassing outage
cause**).
**Containers** vs VMs — ⚠️ **different isolation boundaries; a container escape is a
different risk class from a VM escape.**
**⚠️ Licensing is a genuine architectural constraint in enterprise virtualization** —
**per-core, per-socket and per-VM models change the economics of consolidation
substantially, and licence audits are a real financial exposure.**

---
