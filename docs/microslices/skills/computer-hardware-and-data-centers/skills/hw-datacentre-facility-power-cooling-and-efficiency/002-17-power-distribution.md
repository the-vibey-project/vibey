---
id: skill-17-power-distribution-cfeaf2dd41
purpose: 17 power distribution
source: src/vibey_tools/skills/plugins/computer-hardware-and-data-centers/skills/hw-datacentre-facility-power-cooling-and-efficiency/SKILL.md
requires: ["skill-16-facility-basics-ed669b8217"]
links: ["skill-18-cooling-at-scale-6755de6260"]
---

## §17. ⚠️ Power Distribution

> **⚠️ The dominant capital cost, the dominant design constraint, and increasingly the
> reason a facility can or cannot be built at all** (§26 → `hw-reference`).
```
⚠️ THE CHAIN  utility medium voltage → transformer → switchgear →
   ⚠️ UPS → PDU → rack busbar/PDU → server PSU → VRM → chip
   ⚠️ EVERY CONVERSION LOSES ENERGY, and the losses compound (§19)
⚠️ REDUNDANCY NOTATION  ⚠️ N (no redundancy) · N+1 (one spare) ·
   ⚠️ 2N (fully duplicated) · 2N+1
   ⚠️ THE KEY DISTINCTION: redundancy protects against COMPONENT
   failure; ⚠️ CONCURRENT MAINTAINABILITY means you can also
   service it without downtime, and those are different properties
⚠️ UPS TYPES  ⚠️ double-conversion (cleanest, least efficient) ·
   line-interactive · ⚠️ ECO/multi-mode which trades a little
   protection for meaningful efficiency · flywheel · lithium
   batteries increasingly displacing VRLA
⚠️ GENERATORS  ⚠️ diesel standby, with the UPS covering only the
   seconds until they start and stabilize. ⚠️ FUEL CONTRACTS and
   ⚠️ REGULAR LOAD-BANK TESTING are what make them real — an
   untested generator is a decoration
⚠️ ⚠️ THE FAILURE PATTERN: most data centre outages trace to POWER,
   and disproportionately to the TRANSFER between sources —
   ATS failures, batteries that had degraded silently, and
   generators that didn't start
⚠️ AT RACK LEVEL  ⚠️ 208/415V AC three-phase or 48 VDC, and now
   ⚠️ 800 VDC (§26.2)
```

---
