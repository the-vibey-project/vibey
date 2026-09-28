---
id: skill-23-regulatory-63ff32a0bb
purpose: 23 regulatory
source: src/vibey_tools/skills/plugins/radio-technology-for-software-devs/skills/radio-regulatory-security-and-debugging/SKILL.md
requires: []
links: ["skill-24-what-moved-verified-august-2026-4179363e5a"]
---

## §23. ⚠️ Regulatory

> **⚠️ GOTCHA — this is where software people get their companies in real trouble.**
> ⚠️ **Transmitting is REGULATED. Power limits, duty cycle, band edges and spurious
> emissions are legal requirements, not guidelines** — **and a product that fails
> certification is a product you cannot sell.**

```
ISM BANDS   ⚠️ 433/868 MHz (EU), 915 MHz (US), 2.4 GHz (global), 5 GHz, 6 GHz
   ⚠️ Sub-GHz allocations DIFFER BY REGION — 868 EU vs 915 US is why LoRa
   modules are region-specific and why a design doesn't ship globally unchanged
⚠️ DUTY CYCLE  EU sub-GHz typically limits you to ~1% airtime per hour in
   many sub-bands. ⚠️ This is a HARD design constraint that determines how
   often you can send and interacts brutally with high LoRa spreading factors
POWER LIMITS   ⚠️ EIRP/ERP caps, and antenna gain counts toward them
LISTEN BEFORE TALK · DFS (⚠️ 5 GHz radar avoidance — the AP must vacate a
   channel, which looks like a random outage to your application)
CERTIFICATION  ⚠️ FCC (US) · CE/RED (EU) · UKCA · plus per-country. Pre-certified
   modules transfer most of this burden and are usually the right call
```
**⚠️ Practical advice**: **use a pre-certified module unless you have RF engineers and
volume to justify otherwise**; **plan for regional SKUs from day one if you're using
sub-GHz**; ⚠️ **never ship firmware that lets a user set arbitrary TX power or frequency**;
and **budget for pre-compliance testing before design freeze, not after.**

---
