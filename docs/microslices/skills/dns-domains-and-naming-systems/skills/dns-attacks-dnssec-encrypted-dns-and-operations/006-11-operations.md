---
id: skill-11-operations-53aac4f13c
purpose: 11 operations
source: src/vibey_tools/skills/plugins/dns-domains-and-naming-systems/skills/dns-attacks-dnssec-encrypted-dns-and-operations/SKILL.md
requires: ["skill-10-modern-extensions-43b4004523"]
links: ["skill-12-dns-as-infrastructure-b30deaa498"]
---

## §11. Operations

**⚠️ ANYCAST is the central technique**: ⚠️ **announce the same IP from many locations, and
routing delivers each query to the nearest instance.** ⚠️ **This gives latency reduction,
DDoS absorption and failover simultaneously, and it is how the root and every major provider
operate** (§3 → `dns-namespace-resolution-records-and-zones`).
**⚠️ Diversity is the resilience lesson**: ⚠️ **use nameservers on separate networks and,
ideally, separate PROVIDERS — because a single provider's outage takes your domain off the
internet entirely regardless of how healthy your servers are.**
> **⚠️ GOTCHA — the 2016 Dyn DDoS is the reference case.** ⚠️ **Major sites became
> unreachable not because their infrastructure failed but because their single DNS provider
> was attacked.** **⚠️ Multi-provider DNS is the mitigation, and it is more work than it
> sounds because zone contents must stay synchronized.**

**⚠️ Monitoring**: ⚠️ **query volume and response codes, DNSSEC signature expiry (§8 — set
alerts, because this WILL be what takes you down), delegation consistency, and resolution
from multiple vantage points.**
**⚠️ Registry and registrar locks** (§19 → `dns-whois-disputes-domain-security-and-aftermarket`) belong in the operational runbook, not just in
security policy.

---
