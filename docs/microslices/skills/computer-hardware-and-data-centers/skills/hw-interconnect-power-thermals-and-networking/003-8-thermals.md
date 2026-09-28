---
id: skill-8-thermals-c3bcc151e5
purpose: 8 thermals
source: src/vibey_tools/skills/plugins/computer-hardware-and-data-centers/skills/hw-interconnect-power-thermals-and-networking/SKILL.md
requires: ["skill-7-power-supplies-a2ed6be438"]
links: ["skill-9-networking-591a6c17a0"]
---

## §8. ⚠️ Thermals

> **⚠️ Essentially 100% of electrical power into a computer leaves as heat. Power draw and
> cooling requirement are THE SAME NUMBER, and this equivalence scales all the way to §18 → `hw-datacentre-facility-power-cooling-and-efficiency`.**
```
⚠️ THE THERMAL PATH  die → ⚠️ TIM/solder → IHS → TIM → cold plate
   or heatsink → ⚠️ AIR OR LIQUID → room → outside
   ⚠️ The chain is only as good as its worst link, and the
   die-to-IHS interface is often it
⚠️ THERMAL RESISTANCE in °C/W, summed along the path
⚠️ AIR COOLING  heat pipes (⚠️ phase change, very effective),
   vapour chambers, fin density vs static pressure, ⚠️ and fan
   curves — noise rises steeply with RPM
⚠️ LIQUID  ⚠️ AIO closed loop (⚠️ pump is a wear item and a single
   point of failure) vs custom loop. ⚠️ Water's heat capacity
   moves heat AWAY effectively; ⚠️ it does not create cooling —
   the radiator still rejects to air
⚠️ CASE AIRFLOW  ⚠️ front-to-back, bottom-to-top; positive pressure
   with filtration reduces dust. ⚠️ GPUs dump heat INTO the case,
   which then feeds the CPU cooler
⚠️ ⚠️ THROTTLING IS NORMAL AND BY DESIGN. ⚠️ Modern parts boost
   until they hit a power, thermal or current limit. ⚠️ Therefore
   BETTER COOLING IS A PERFORMANCE UPGRADE, not just a quiet one
⚠️ TIM  ⚠️ application method matters far less than people argue
   about; ⚠️ pump-out and dry-out over years is real
```

---
