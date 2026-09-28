---
id: skill-19-efficiency-metrics-763a202e00
purpose: 19 efficiency metrics
source: src/vibey_tools/skills/plugins/computer-hardware-and-data-centers/skills/hw-datacentre-facility-power-cooling-and-efficiency/SKILL.md
requires: ["skill-18-cooling-at-scale-6755de6260"]
links: ["skill-20-racks-and-physical-infrastructure-770ecf8670"]
---

## §19. Efficiency Metrics

**⚠️ PUE = total facility energy ÷ IT equipment energy.** ⚠️ **1.0 is the theoretical
ideal; hyperscale facilities operate close to it and legacy enterprise rooms are far
worse.**
> **⚠️ GOTCHA — PUE IS EASILY GAMED AND FREQUENTLY MISUSED.** ⚠️ **It measures
> INFRASTRUCTURE overhead, not useful work.** **⚠️ Making the IT equipment less efficient
> IMPROVES PUE, because it increases the denominator.** ⚠️ **A facility with excellent PUE
> running idle servers is wasting more energy than a worse-PUE facility doing useful work.**
> **⚠️ Also check the measurement boundary, the averaging period, and whether it's
> annualized or a favourable-day figure.**

**⚠️ Complementary metrics**: ⚠️ **WUE (water), CUE (carbon), and — the ones that actually
matter — WORK PER WATT: transactions, queries or tokens per joule.**
**⚠️ The largest efficiency wins are usually not in the facility at all**: ⚠️ **server
utilization (⚠️ idle servers draw a large fraction of peak power for zero output),
virtualization and consolidation, decommissioning zombie servers, and software
efficiency.**

---
