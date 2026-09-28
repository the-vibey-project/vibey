---
id: skill-1-what-dns-is-for-e0585e14c4
purpose: 1 what dns is for
source: src/vibey_tools/skills/plugins/dns-domains-and-naming-systems/skills/dns-namespace-resolution-records-and-zones/SKILL.md
requires: ["skill-0-routing-053ae37fde"]
links: ["skill-2-the-namespace-c69b07636b"]
---

## §1. What DNS Is For

```
⚠️ THE OBVIOUS JOB  ⚠️ name → IP address
⚠️ ⚠️ THE LESS OBVIOUS AND MORE IMPORTANT JOBS
   ⚠️ INDIRECTION  ⚠️ change where a name points without
      changing the name. ⚠️ This is what makes the whole web
      operable — hosts move, providers change, the name persists
   ⚠️ SERVICE DISCOVERY  ⚠️ MX for mail, SRV for services,
      NAPTR — ⚠️ DNS is how you find WHICH machine does WHAT
   ⚠️ ⚠️ POLICY DISTRIBUTION  ⚠️ SPF, DKIM, DMARC, CAA, DNSSEC
      records — ⚠️ DNS became the internet's general-purpose
      public assertion mechanism for a domain, largely by
      accident
   ⚠️ TRAFFIC STEERING  geographic and load-based (§12)
⚠️ ⚠️ AND THE UNDERAPPRECIATED ONE: DNS IS THE BASIS OF WEB PKI
   IDENTITY. ⚠️ A certificate authority proves you control a
   name by checking DNS or a resource under it — ⚠️ so whoever
   controls your DNS can obtain certificates for you (§19)
⚠️ THE SCALE  ⚠️ hundreds of millions of domains, trillions of
   queries daily, sub-100ms expectations, on a protocol from
   1983 with UDP as the default transport
```

---

# PART I — THE PROTOCOL
