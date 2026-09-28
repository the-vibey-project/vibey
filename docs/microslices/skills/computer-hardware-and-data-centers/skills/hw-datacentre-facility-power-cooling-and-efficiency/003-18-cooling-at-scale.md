---
id: skill-18-cooling-at-scale-6755de6260
purpose: 18 cooling at scale
source: src/vibey_tools/skills/plugins/computer-hardware-and-data-centers/skills/hw-datacentre-facility-power-cooling-and-efficiency/SKILL.md
requires: ["skill-17-power-distribution-cfeaf2dd41"]
links: ["skill-19-efficiency-metrics-763a202e00"]
---

## §18. ⚠️ Cooling at Scale

**⚠️ Every watt in becomes a watt of heat out** (§8 → `hw-interconnect-power-thermals-and-networking`) — ⚠️ **so a 100 MW facility is a 100 MW
heat source.** **See a refrigeration reference for the underlying physics.**
```
⚠️ AIR-BASED  ⚠️ hot aisle / cold aisle containment (⚠️ the single
   highest-value retrofit in legacy facilities) · CRAC/CRAH ·
   raised floor or overhead delivery
   ⚠️ AIR RUNS OUT OF CAPACITY around 30-40 kW per rack even
   with optimized design (§26.2)
⚠️ ECONOMIZATION  ⚠️ air-side (⚠️ outside air directly, subject to
   humidity and contamination) and water-side (cooling towers)
   ⚠️ FREE COOLING HOURS drive site selection
⚠️ LIQUID  ⚠️ rear-door heat exchangers (⚠️ easiest retrofit) →
   ⚠️ DIRECT-TO-CHIP cold plates with a CDU → immersion
   (single or two-phase)
   ⚠️ Liquid is now MANDATORY, not optional, above roughly
   50-100 kW per rack (§26.2)
⚠️ WATER  ⚠️ evaporative cooling consumes water and trades it
   against electricity. ⚠️ WUE is a real metric and a real siting
   constraint in stressed regions
⚠️ ⚠️ ASHRAE THERMAL GUIDELINES  ⚠️ and the important finding is
   that the allowable ranges are WIDER than operators historically
   assumed — running warmer saves substantial cooling energy at
   little reliability cost, and over-cooling is a widespread and
   expensive habit
⚠️ HEAT REUSE  district heating from data centre waste heat is
   real where the geography permits, and limited by the LOW
   TEMPERATURE of the rejected heat (see a thermodynamics
   reference on exergy)
```

---
