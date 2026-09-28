---
id: skill-6-caching-and-ttl-60cc068ac9
purpose: 6 caching and ttl
source: src/vibey_tools/skills/plugins/dns-domains-and-naming-systems/skills/dns-attacks-dnssec-encrypted-dns-and-operations/SKILL.md
requires: []
links: ["skill-7-attacks-on-dns-fbd7b8c62a"]
---

## §6. ⚠️ Caching and TTL

> **⚠️ §1 → `dns-namespace-resolution-records-and-zones`'s second organizing idea, and the operational one that matters most.**
```
⚠️ ⚠️ "DNS PROPAGATION" IS NOT A THING. ⚠️ Nothing propagates.
   ⚠️ Authoritative data changes INSTANTLY. What takes time is
   CACHED OLD ANSWERS EXPIRING
   ⚠️ THEREFORE the delay is bounded by the TTL THAT WAS IN
   EFFECT WHEN THE OLD ANSWER WAS CACHED — ⚠️ lowering the TTL
   now does not speed up a change you make now
⚠️ ⚠️ THE CORRECT PROCEDURE FOR A PLANNED CHANGE
   ⚠️ 1. LOWER THE TTL (say to 300s) · ⚠️ 2. WAIT for the OLD
   TTL to elapse · ⚠️ 3. make the change · 4. verify ·
   ⚠️ 5. raise the TTL back
⚠️ TTL AS A TRADE  ⚠️ short = agility and more query load and
   more exposure to resolver failures; long = efficiency and
   slow to change. ⚠️ Long for stable records, short before
   migrations
⚠️ ⚠️ TTLs ARE ADVISORY. ⚠️ Some resolvers clamp minimums, some
   serve stale on failure (⚠️ RFC 8767, which is a deliberate
   resilience feature), browsers cache separately, and the OS
   caches too. ⚠️ You do not control the whole chain
⚠️ NEGATIVE CACHING is governed by the SOA minimum — ⚠️ so
   creating a record that was recently missing can take longer
   to appear than changing an existing one
```

---
