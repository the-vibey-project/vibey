---
id: skill-30-quick-reference-e1b33825df
purpose: 30 quick reference
source: src/vibey_tools/skills/plugins/dns-domains-and-naming-systems/skills/dns-reference/SKILL.md
requires: ["skill-29-sources-852ad2ca58"]
links: ["skill-31-method-0b8f48c9e6"]
---

## §30. Quick Reference

### 30.1 Picker
| Question | Where |
|---|---|
| Why hasn't my DNS change taken effect? | ⚠️ **The old TTL. Nothing propagates** (§6 → `dns-attacks-dnssec-encrypted-dns-and-operations`) |
| How do I migrate without downtime? | ⚠️ **Lower TTL, wait the OLD TTL, then change** (§6 → `dns-attacks-dnssec-encrypted-dns-and-operations`) |
| Domain works for some people only | ⚠️ **Delegation mismatch or missing glue** (§5 → `dns-namespace-resolution-records-and-zones`) |
| Can I CNAME my apex? | ⚠️ **No. Use ALIAS/HTTPS records — provider-specific** (§4 → `dns-namespace-resolution-records-and-zones`, §10 → `dns-attacks-dnssec-encrypted-dns-and-operations`) |
| Should I enable DNSSEC? | ⚠️ **Yes with monitoring; expiry will take you down** (§8 → `dns-attacks-dnssec-encrypted-dns-and-operations`, §11 → `dns-attacks-dnssec-encrypted-dns-and-operations`) |
| Is my domain secure? | ⚠️ **Registry lock, MFA, CAA, expiry monitoring** (§19 → `dns-whois-disputes-domain-security-and-aftermarket`) |
| Someone took over my subdomain | ⚠️ **Dangling CNAME to a reclaimed cloud resource** (§19 → `dns-whois-disputes-domain-security-and-aftermarket`) |
| I let a domain expire | ⚠️ **Check where it is in the lifecycle. Act fast** (§16 → `dns-icann-tlds-registries-and-registration`) |
| Is .io safe for my brand? | ⚠️ **It's a ccTLD. Sovereign risk is real** (§14 → `dns-icann-tlds-registries-and-registration`) |
| Should I buy a .eth domain? | ⚠️ **For crypto identity yes; as a web address no** (§24 → `dns-blockchain-naming-alternatives-assessed`) |
| Should I apply for a gTLD? | ⚠️ **$227k, an RSP, and years. 2026 window closed 12 Aug (1,600+ applied)** (§26.1) |
| Do I need to defend my trademark? | ⚠️ **Get marks into the Clearinghouse before launches** (§18 → `dns-whois-disputes-domain-security-and-aftermarket`, §26.1) |

### 30.2 Domain hygiene checklist
- [ ] ⚠️ **Registry lock on anything significant** (§19 → `dns-whois-disputes-domain-security-and-aftermarket`)
- [ ] ⚠️ **MFA on the registrar account, monitored contact address** (§19 → `dns-whois-disputes-domain-security-and-aftermarket`)
- [ ] ⚠️ **Auto-renew on, with a payment card that will not expire first** (§16 → `dns-icann-tlds-registries-and-registration`, §19 → `dns-whois-disputes-domain-security-and-aftermarket`)
- [ ] Expiry monitored INDEPENDENTLY of the registrar (§19 → `dns-whois-disputes-domain-security-and-aftermarket`)
- [ ] ⚠️ **CAA records restricting certificate issuance** (§4 → `dns-namespace-resolution-records-and-zones`, §19 → `dns-whois-disputes-domain-security-and-aftermarket`)
- [ ] Certificate Transparency monitoring for your names (§19 → `dns-whois-disputes-domain-security-and-aftermarket`)
- [ ] ⚠️ **Nameservers on diverse networks, ideally diverse providers** (§11 → `dns-attacks-dnssec-encrypted-dns-and-operations`)
- [ ] ⚠️ **Parent and child NS records agree; glue correct** (§5 → `dns-namespace-resolution-records-and-zones`)
- [ ] DNSSEC signed, with signature-expiry alerting (§8 → `dns-attacks-dnssec-encrypted-dns-and-operations`, §11 → `dns-attacks-dnssec-encrypted-dns-and-operations`)
- [ ] ⚠️ **Dangling CNAME/NS records audited regularly** (§19 → `dns-whois-disputes-domain-security-and-aftermarket`)
- [ ] AXFR restricted (§5 → `dns-namespace-resolution-records-and-zones`)
- [ ] ⚠️ **TTLs deliberate — short before a migration, long otherwise** (§6 → `dns-attacks-dnssec-encrypted-dns-and-operations`)

---
