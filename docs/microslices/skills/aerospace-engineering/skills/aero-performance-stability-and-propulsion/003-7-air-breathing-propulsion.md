---
id: skill-7-air-breathing-propulsion-72086cbbc8
purpose: 7 air breathing propulsion
source: src/vibey_tools/skills/plugins/aerospace-engineering/skills/aero-performance-stability-and-propulsion/SKILL.md
requires: ["skill-6-stability-and-control-ea2fc7e91a"]
links: []
---

## §7. Air-Breathing Propulsion

**⚠️ Brayton cycle**: intake → compressor → combustor → turbine → nozzle.
```
Turbojet     ⚠️ high exhaust velocity — efficient only at high speed
Turbofan     ⚠️ bypass air accelerated moderately. HIGH BYPASS = high efficiency
             at subsonic speed. This is why airliners look the way they do
Turboprop    very high mass flow, low velocity; ⚠️ best below ~M 0.6
Turboshaft   helicopters
Ramjet       ⚠️ no moving compressor — needs M > ~2 and can't start from rest
Scramjet     supersonic combustion, M > 5
Piston/electric   light aircraft, drones (§11)
```
> **⚠️ GOTCHA — the propulsive efficiency principle explains the whole table.**
> ⚠️ **`η_p ≈ 2/(1 + V_exhaust/V_aircraft)`.** **Efficiency is maximized when exhaust
> velocity is only slightly above flight velocity** — **so for a given thrust, accelerating
> a LARGE mass of air a LITTLE beats accelerating a small mass a lot.** **That single
> relation is why bypass ratios climbed from 1 to 12+, why propellers beat jets at low
> speed, and why a helicopter rotor is enormous.**

**⚠️ Thrust falls with altitude** (density) **and with airspeed** for a turbojet; **thermal
efficiency rises with pressure ratio and turbine inlet temperature** — ⚠️ **which is why
turbine blade materials and cooling are the technology that gates engine performance.**
**Single-crystal superalloys with film cooling run above the alloy's melting point.**
