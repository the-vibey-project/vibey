---
id: skill-21-batteries-and-degradation-eeb5036a77
purpose: 21 batteries and degradation
source: src/vibey_tools/skills/plugins/how-cars-work-and-how-mechanics-work/skills/car-electrical-networks-adas-ev-and-high-voltage-safety/SKILL.md
requires: ["skill-20-ev-architecture-daa7dff761"]
links: ["skill-22-high-voltage-safety-aeeee4f1a6"]
---

## §21. Batteries and Degradation

**⚠️ Chemistry**: **NMC (higher energy density) vs LFP (⚠️ longer cycle life, more tolerant
of full charging, less energy dense, weaker in cold).**
**⚠️ Degradation drivers, in rough order**: ⚠️ **heat, time (calendar ageing), high state of
charge dwelling, deep cycling, and frequent DC fast charging.** **⚠️ Which is why the
standard advice is 20–80% for daily use and full charges before long trips only** —
**⚠️ with LFP being the exception, where periodic full charges are recommended for BMS
calibration.**
**⚠️ State of Health vs State of Charge**: ⚠️ **SoH is capacity relative to new and is what
matters for a used EV purchase; ⚠️ and pack-level SoH readings vary by tool and method,
so treat single readings cautiously.**
**⚠️ Repairability is the live commercial question**: ⚠️ **module-level and cell-level repair
is technically feasible and often blocked by design, pack construction (structural packs,
glued cells) or data access** — **which is why relatively minor pack damage can total a
vehicle** (§30.1 → `car-reference`).

---
