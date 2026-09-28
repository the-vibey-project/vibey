---
id: skill-27-misconceptions-e3974e3337
purpose: 27 misconceptions
source: src/vibey_tools/skills/plugins/dns-domains-and-naming-systems/skills/dns-reference/SKILL.md
requires: ["skill-26-what-s-live-checked-august-2026-88298d680c"]
links: ["skill-28-numbers-and-dates-57884117c8"]
---

## §27. Misconceptions

| Misconception | Correction |
|---|---|
| DNS propagation takes 48 hours | ⚠️ **Nothing propagates. Old cached answers expire** (§6 → `dns-attacks-dnssec-encrypted-dns-and-operations`) |
| Lowering TTL now speeds up my change | ⚠️ **The OLD TTL governs. Lower it first, then wait** (§6 → `dns-attacks-dnssec-encrypted-dns-and-operations`) |
| There are 13 root servers | ⚠️ **13 named addresses, anycast to hundreds of instances** (§3 → `dns-namespace-resolution-records-and-zones`, §11 → `dns-attacks-dnssec-encrypted-dns-and-operations`) |
| The root knows where domains are | ⚠️ **It only knows TLD delegations. Referral, not lookup** (§3 → `dns-namespace-resolution-records-and-zones`) |
| You can CNAME the apex | ⚠️ **No — SOA and NS live there. Hence ALIAS hacks** (§4 → `dns-namespace-resolution-records-and-zones`, §10 → `dns-attacks-dnssec-encrypted-dns-and-operations`) |
| DNSSEC encrypts DNS | ⚠️ **Integrity only. Everything stays visible** (§8 → `dns-attacks-dnssec-encrypted-dns-and-operations`, §9 → `dns-attacks-dnssec-encrypted-dns-and-operations`) |
| DNSSEC is strictly safer | ⚠️ **Misconfiguration takes you fully offline** (§8 → `dns-attacks-dnssec-encrypted-dns-and-operations`) |
| DoH is straightforwardly a privacy win | ⚠️ **It moves trust to a few large providers** (§9 → `dns-attacks-dnssec-encrypted-dns-and-operations`) |
| Encrypted DNS hides the site you visit | ⚠️ **Not without ECH — SNI leaks it** (§9 → `dns-attacks-dnssec-encrypted-dns-and-operations`) |
| DNS failover works quickly | ⚠️ **TTLs are advisory; clients cache hard** (§6 → `dns-attacks-dnssec-encrypted-dns-and-operations`, §12 → `dns-attacks-dnssec-encrypted-dns-and-operations`) |
| One good DNS provider is enough | ⚠️ **Single-provider outage = domain gone. See Dyn 2016** (§11 → `dns-attacks-dnssec-encrypted-dns-and-operations`) |
| You own your domain | ⚠️ **You hold a renewable registration** (§15 → `dns-icann-tlds-registries-and-registration`) |
| The registrar is the registry | ⚠️ **Three distinct parties. Know which to escalate to** (§15 → `dns-icann-tlds-registries-and-registration`) |
| An expired domain is gone | ⚠️ **Grace, then redemption, then pending delete** (§16 → `dns-icann-tlds-registries-and-registration`) |
| .io and .ai are generic | ⚠️ **They're country codes with sovereign risk** (§14 → `dns-icann-tlds-registries-and-registration`) |
| WHOIS redaction was ICANN policy | ⚠️ **It was GDPR. RDAP is the structured answer** (§17 → `dns-whois-disputes-domain-security-and-aftermarket`) |
| UDRP means trademarks always win | ⚠️ **Three elements including bad faith. RDNH is findable** (§18 → `dns-whois-disputes-domain-security-and-aftermarket`) |
| Domain security is about DNSSEC | ⚠️ **Mostly account security, expiry and registry lock** (§19 → `dns-whois-disputes-domain-security-and-aftermarket`) |
| Subdomain takeover is exotic | ⚠️ **Dangling CNAMEs are extremely common** (§19 → `dns-whois-disputes-domain-security-and-aftermarket`) |
| Blockchain domains replace DNS | ⚠️ **No browser resolves them natively. That was fatal** (§24 → `dns-blockchain-naming-alternatives-assessed`, §26.2) |
| Web3 names are censorship-proof | ⚠️ **The name maybe; hosting, gateways and exchanges aren't** (§24 → `dns-blockchain-naming-alternatives-assessed`) |
| "Own it forever, no renewals" | ⚠️ **True of the token, contingent on the infrastructure** (§24 → `dns-blockchain-naming-alternatives-assessed`) |
| Decentralized naming is strictly better | ⚠️ **Multiple roots means the same name resolves differently** (§21 → `dns-blockchain-naming-alternatives-assessed`) |
| ENS is fighting ICANN | ⚠️ **It applied for .ens in ICANN's 2026 round** (§26.2) |
| Web3 naming failed on technology | ⚠️ **It failed on distribution — the classic alt-root problem** (§24 → `dns-blockchain-naming-alternatives-assessed`, §26.2) |

---
