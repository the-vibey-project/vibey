---
id: skill-10-modern-extensions-43b4004523
purpose: 10 modern extensions
source: src/vibey_tools/skills/plugins/dns-domains-and-naming-systems/skills/dns-attacks-dnssec-encrypted-dns-and-operations/SKILL.md
requires: ["skill-9-encrypted-dns-936017aa21"]
links: ["skill-11-operations-53aac4f13c"]
---

## §10. Modern Extensions

**⚠️ EDNS0** carries larger messages and option codes; ⚠️ **EDNS Client Subnet passes a
truncated client address to authoritative servers for geographic steering — ⚠️ useful for
CDNs and a genuine privacy leak, which is why some resolvers refuse it.**
**⚠️ The apex CNAME problem** (§4 → `dns-namespace-resolution-records-and-zones`) and its workarounds: ⚠️ **ALIAS/ANAME/CNAME-flattening
are PROVIDER-SPECIFIC, non-standard, and resolve server-side — which means behaviour differs
between DNS hosts.**
**⚠️ SVCB and HTTPS records** are the standardized fix and are genuinely significant:
⚠️ **they let a name advertise its protocol support, alternative endpoints, ECH
configuration and IP hints IN ONE LOOKUP — removing a round trip and enabling
HTTP/3 and ECH discovery without a redirect.**
**⚠️ Multicast DNS and DNS-SD** for local discovery (`.local`, and how printers and Chromecasts
are found).
**⚠️ DNS cookies and RRL** for spoofing and amplification resistance (§7).

---
