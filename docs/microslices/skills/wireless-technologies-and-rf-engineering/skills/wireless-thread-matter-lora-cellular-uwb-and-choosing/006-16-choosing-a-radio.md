---
id: skill-16-choosing-a-radio-4d8b5e4a2e
purpose: 16 choosing a radio
source: src/vibey_tools/skills/plugins/wireless-technologies-and-rf-engineering/skills/wireless-thread-matter-lora-cellular-uwb-and-choosing/SKILL.md
requires: ["skill-15-other-technologies-worth-knowing-855eee8df0"]
links: []
---

## §16. Choosing a Radio

```
⚠️ THE DECISION ORDER — ⚠️ answer these before picking a chip
   ⚠️ 1. RANGE and environment · 2. DATA RATE and duty cycle ·
   ⚠️ 3. POWER SOURCE — battery life target is the harshest
      constraint and drives everything (§19)
   ⚠️ 4. Latency requirement · 5. Number of nodes and topology ·
   ⚠️ 6. What must it talk TO? (⚠️ if a phone must connect
      directly, that means BLE or Wi-Fi, full stop)
   ⚠️ 7. Infrastructure — does a gateway exist? · 8. Regions to sell
⚠️ MODULE vs CHIP-DOWN
   ⚠️ PRE-CERTIFIED MODULE  ⚠️ dramatically cheaper and faster for
      low and medium volume, because it carries modular
      certification (§18). ⚠️ Higher unit cost
   ⚠️ CHIP-DOWN  cheapest at volume, ⚠️ full certification burden
      and RF layout expertise required
   ⚠️ ⚠️ FOR MOST PROJECTS, USE A MODULE. The certification saving
      alone usually exceeds the unit-cost penalty
⚠️ ECOSYSTEM MATTERS AS MUCH AS SILICON  ⚠️ SDK quality,
   documentation, stack maturity, long-term availability, and
   whether you can get support
```
