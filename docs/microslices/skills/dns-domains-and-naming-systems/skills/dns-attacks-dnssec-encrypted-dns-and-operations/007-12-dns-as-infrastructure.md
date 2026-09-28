---
id: skill-12-dns-as-infrastructure-b30deaa498
purpose: 12 dns as infrastructure
source: src/vibey_tools/skills/plugins/dns-domains-and-naming-systems/skills/dns-attacks-dnssec-encrypted-dns-and-operations/SKILL.md
requires: ["skill-11-operations-53aac4f13c"]
links: []
---

## §12. DNS as Infrastructure

**⚠️ CDN and global load balancing**: ⚠️ **answer differently by client location or server
health — which is DNS being used as a control plane, and it works because of §1 → `dns-namespace-resolution-records-and-zones`'s
indirection.**
> **⚠️ GOTCHA — DNS is a poor failover mechanism and people rely on it anyway.** ⚠️ **TTLs
> are advisory (§6), clients cache aggressively, and a browser may hold a resolved address
> for the life of a session.** **⚠️ Expect a long tail of traffic to the old address after
> any DNS-based failover, and design for it.**

**⚠️ Service discovery** in Kubernetes and elsewhere — ⚠️ **and note that cluster DNS
becomes a critical dependency whose failure looks like everything failing at once.**
**⚠️ DNS for blocklists and reputation** (RBLs for mail, §6 of a communications reference)
and ⚠️ **for filtering — which is what DoH (§9) disrupts.**
**⚠️ DNS as a covert channel**: ⚠️ **tunnelling and exfiltration over DNS work because DNS
is almost never blocked, and detecting them is a standard security-monitoring task.**

---

# PART II — DOMAINS AND GOVERNANCE
