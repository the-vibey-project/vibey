---
id: skill-5-zones-delegation-and-glue-fff60db48e
purpose: 5 zones delegation and glue
source: src/vibey_tools/skills/plugins/dns-domains-and-naming-systems/skills/dns-namespace-resolution-records-and-zones/SKILL.md
requires: ["skill-4-record-types-e482acf209"]
links: []
---

## §5. ⚠️ Zones, Delegation and Glue

```
⚠️ A ZONE is an administrative unit — ⚠️ a contiguous part of the
   tree managed together, bounded by delegations
⚠️ ⚠️ DELEGATION  ⚠️ the PARENT publishes NS records pointing to
   the child's servers. ⚠️ The parent does not hold the child's
   data — it only says who does
⚠️ ⚠️ THE NS RECORDS EXIST IN TWO PLACES — ⚠️ in the parent
   (authoritative for delegation) and in the child zone itself.
   ⚠️ When they disagree, resolution becomes unpredictable, and
   this is a real and common misconfiguration
⚠️ ⚠️ GLUE RECORDS  ⚠️ if example.com's nameserver is
   ns1.example.com, you have a CIRCULAR DEPENDENCY — you need
   the nameserver's address to look up the nameserver.
   ⚠️ The PARENT supplies the address directly. That is glue
   ⚠️ ⚠️ MISSING OR STALE GLUE IS A CLASSIC CAUSE OF A DOMAIN
   THAT WORKS FOR SOME PEOPLE AND NOT OTHERS
⚠️ ZONE TRANSFER  ⚠️ AXFR (full) and IXFR (incremental) with
   NOTIFY. ⚠️ Restrict AXFR — an open one hands an attacker
   your entire internal namespace
⚠️ PRIMARY and SECONDARY servers, ⚠️ and hidden primaries
⚠️ ⚠️ LAME DELEGATION  ⚠️ a nameserver is listed but does not
   answer authoritatively. ⚠️ Slow, intermittent failures
```
