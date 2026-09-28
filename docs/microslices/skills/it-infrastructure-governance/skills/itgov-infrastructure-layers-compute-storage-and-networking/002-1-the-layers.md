---
id: skill-1-the-layers-06964e8a32
purpose: 1 the layers
source: src/vibey_tools/skills/plugins/it-infrastructure-governance/skills/itgov-infrastructure-layers-compute-storage-and-networking/SKILL.md
requires: ["skill-0-routing-f940dd52d3"]
links: ["skill-2-compute-and-virtualization-ebf237b364"]
---

## §1. The Layers

```
FACILITY      power, cooling, physical security  (see a power engineering reference §12)
COMPUTE       servers, hypervisors, containers
STORAGE       block, file, object; SAN/NAS
NETWORK       switching, routing, firewalls, load balancing, WAN
PLATFORM      OS, middleware, databases
IDENTITY      ⚠️ directory, authentication, authorization — the control plane
APPLICATION   the things people actually use
⚠️ GOVERNANCE  policy, process, evidence — wraps all of it
```
**⚠️ The hybrid reality is the normal case and worth stating plainly**: **very few
organizations are all-cloud or all-on-prem.** ⚠️ **Most run on-prem Active Directory
synchronized to a cloud identity provider, some workloads in a datacentre and some in
cloud, and the seams between them are where both the operational pain and the security
gaps live.**

---
