---
id: skill-3-resolution-31f0d7a086
purpose: 3 resolution
source: src/vibey_tools/skills/plugins/dns-domains-and-naming-systems/skills/dns-namespace-resolution-records-and-zones/SKILL.md
requires: ["skill-2-the-namespace-c69b07636b"]
links: ["skill-4-record-types-e482acf209"]
---

## §3. ⚠️ Resolution

> **⚠️ Knowing the two different kinds of server is what makes DNS debugging tractable.**
```
⚠️ ⚠️ THE TWO ROLES, and conflating them causes endless confusion
   ⚠️ RECURSIVE RESOLVER  ⚠️ does the WORK on your behalf —
      walks the hierarchy, caches results. ⚠️ Your ISP's, or
      8.8.8.8, or 1.1.1.1
   ⚠️ AUTHORITATIVE SERVER  ⚠️ holds the actual zone data for a
      domain and answers only for it. ⚠️ It does NOT recurse
⚠️ THE WALK, for a cold cache
   ⚠️ 1. Ask a ROOT server → "I don't know, but ask the .com
      servers, here they are"
   ⚠️ 2. Ask a .com server → "ask example.com's servers"
   ⚠️ 3. Ask example.com's server → the answer
   ⚠️ ⚠️ EACH STEP IS A REFERRAL, NOT A LOOKUP. The root does not
      know about your domain and never will
⚠️ STUB RESOLVER  ⚠️ what's in your OS — it just asks a recursive
   resolver and believes the answer
⚠️ ⚠️ THE 13 ROOT SERVER "ADDRESSES" ARE NOT 13 MACHINES.
   ⚠️ Thirteen is the count of NAMED addresses (a UDP packet
   size constraint from the original design); ⚠️ each is
   ANYCAST to hundreds of physical instances worldwide (§11)
⚠️ TRANSPORT  ⚠️ UDP 53 by default with a 512-byte classic limit,
   ⚠️ EDNS0 for larger, ⚠️ TCP fallback on truncation — and
   ⚠️ blocking DNS over TCP breaks things in confusing ways
⚠️ NEGATIVE ANSWERS  NXDOMAIN, and ⚠️ SOA-governed negative
   caching means "no such name" is cached too
```

---
