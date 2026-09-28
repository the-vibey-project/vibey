---
id: skill-4-record-types-e482acf209
purpose: 4 record types
source: src/vibey_tools/skills/plugins/dns-domains-and-naming-systems/skills/dns-namespace-resolution-records-and-zones/SKILL.md
requires: ["skill-3-resolution-31f0d7a086"]
links: ["skill-5-zones-delegation-and-glue-fff60db48e"]
---

## §4. Record Types

```
⚠️ THE COMMON ONES
   ⚠️ A / AAAA  IPv4 / IPv6 address
   ⚠️ CNAME  ⚠️ an ALIAS to another NAME. ⚠️ Cannot coexist with
      other records at the same name — ⚠️ WHICH IS WHY YOU
      CANNOT PUT A CNAME AT THE ZONE APEX (the apex needs SOA
      and NS). ⚠️ This trips up nearly everyone once (§10)
   ⚠️ MX  mail exchanger, with preference values
   ⚠️ TXT  ⚠️ arbitrary text — and therefore SPF, DKIM, DMARC,
      and domain-ownership verification for every SaaS product
   ⚠️ NS  delegation (§5) · ⚠️ SOA  zone parameters and the
      negative-cache TTL
   ⚠️ PTR  reverse lookup, ⚠️ and mail servers genuinely check it
   ⚠️ SRV  service location — host, port, priority, weight
   ⚠️ CAA  ⚠️ which certificate authorities may issue for this
      name. ⚠️ Cheap, underused, and directly limits the §19
      attack
   ⚠️ DNSKEY, DS, RRSIG, NSEC/NSEC3  DNSSEC (§8)
   ⚠️ SVCB / HTTPS  ⚠️ the modern one (§10)
⚠️ RRSET  ⚠️ all records of one type at one name are handled and
   signed as a SET, not individually
```

---
