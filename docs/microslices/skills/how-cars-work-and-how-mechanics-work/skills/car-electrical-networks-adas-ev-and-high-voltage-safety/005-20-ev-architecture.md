---
id: skill-20-ev-architecture-daa7dff761
purpose: 20 ev architecture
source: src/vibey_tools/skills/plugins/how-cars-work-and-how-mechanics-work/skills/car-electrical-networks-adas-ev-and-high-voltage-safety/SKILL.md
requires: ["skill-19-air-conditioning-f126bb37fd"]
links: ["skill-21-batteries-and-degradation-eeb5036a77"]
---

## §20. EV Architecture

```
⚠️ HIGH VOLTAGE BATTERY (400 V or 800 V) → inverter → motor
   ⚠️ 800 V architectures enable faster charging at lower current
⚠️ BMS  monitors cell voltages and temperatures, balances cells,
   enforces limits. ⚠️ Effectively the battery's ECU
⚠️ ON-BOARD CHARGER (AC) vs ⚠️ DC FAST CHARGING (bypasses it, feeds
   the pack directly)
⚠️ DC-DC CONVERTER  ⚠️ replaces the alternator, running the 12V system
   from the HV pack. ⚠️ EVs still have a 12V battery, and a dead 12V
   battery immobilizes an EV completely — a very common call-out
MOTORS  permanent magnet synchronous (efficient) · induction (no
   rare-earth magnets) · ⚠️ one-speed reduction gear, no gearbox
⚠️ THERMAL MANAGEMENT  liquid cooling/heating of the pack;
   ⚠️ heat pumps for cabin heat (resistance heating destroys winter range)
```
**⚠️ What EVs still need serviced**: ⚠️ **tyres (⚠️ heavier vehicles and instant torque wear
them faster), brakes (§14 → `car-transmissions-driveline-suspension-steering-brakes-and-tyres`'s seizing problem), suspension, steering, HVAC, coolant,
cabin filter, 12V battery and software.** **⚠️ What disappears: oil changes, spark plugs,
timing belts, exhaust and fuel systems.**

---
