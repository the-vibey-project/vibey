---
id: skill-34-quick-reference-c954abca9c
purpose: 34 quick reference
source: src/vibey_tools/skills/plugins/how-cars-work-and-how-mechanics-work/skills/car-reference/SKILL.md
requires: ["skill-33-books-and-resources-2d89a3116f"]
links: ["skill-35-method-4e411f26a1"]
---

## §34. Quick Reference

### 34.1 Diagnostic picker
| Symptom | Where |
|---|---|
| Any running fault | ⚠️ **Air, fuel, spark, compression, timing** (§25 → `car-diagnostic-method-obd-tools-and-shop-economics`) |
| Lean or rich code | ⚠️ **Read FUEL TRIMS at idle AND load** (§6 → `car-engine-cycle-fuel-ignition-management-and-emissions`, §26 → `car-diagnostic-method-obd-tools-and-shop-economics`) |
| Lean at idle only | ⚠️ **Vacuum leak — smoke test** (§6 → `car-engine-cycle-fuel-ignition-management-and-emissions`, §27 → `car-diagnostic-method-obd-tools-and-shop-economics`) |
| Lean at load only | ⚠️ **Fuel delivery or MAF** (§6 → `car-engine-cycle-fuel-ignition-management-and-emissions`) |
| Misfire | ⚠️ **Isolate cylinder, then ignition vs fuel vs compression** (§25 → `car-diagnostic-method-obd-tools-and-shop-economics`) |
| Overheats at idle, fine moving | ⚠️ **Cooling fan** (§7 → `car-engine-cycle-fuel-ignition-management-and-emissions`) |
| Overheats always, no leak | ⚠️ **Thermostat, pump, or head gasket — block test** (§7 → `car-engine-cycle-fuel-ignition-management-and-emissions`) |
| Many unrelated faults at once | ⚠️ **Ground or CAN** (§16 → `car-electrical-networks-adas-ev-and-high-voltage-safety`, §17 → `car-electrical-networks-adas-ev-and-high-voltage-safety`) |
| Battery dies overnight | ⚠️ **Parasitic draw, after modules sleep** (§16 → `car-electrical-networks-adas-ev-and-high-voltage-safety`) |
| Judder under braking | ⚠️ **DTV/pad transfer, not "warped"** (§14 → `car-transmissions-driveline-suspension-steering-brakes-and-tyres`) |
| Shudder at steady cruise | ⚠️ **Torque converter lock-up** (§10 → `car-transmissions-driveline-suspension-steering-brakes-and-tyres`) |
| Pull to one side | ⚠️ **Swap front tyres first — free test** (§13 → `car-transmissions-driveline-suspension-steering-brakes-and-tyres`) |
| Tyre wearing on one edge | ⚠️ **Camber. Feathered → toe. Cupped → dampers** (§15 → `car-transmissions-driveline-suspension-steering-brakes-and-tyres`) |
| Clicking on turns | ⚠️ **Outer CV joint** (§11 → `car-transmissions-driveline-suspension-steering-brakes-and-tyres`) |
| Safety system light after bodywork | ⚠️ **Calibration** (§18 → `car-electrical-networks-adas-ev-and-high-voltage-safety`) |
| EV completely dead | ⚠️ **12V battery** (§20 → `car-electrical-networks-adas-ev-and-high-voltage-safety`) |
| Diesel warning light, short trips | ⚠️ **DPF regeneration never completing** (§8 → `car-engine-cycle-fuel-ignition-management-and-emissions`) |

### 34.2 Before you replace anything
- [ ] ⚠️ **Complaint verified and reproduced** (§25 → `car-diagnostic-method-obd-tools-and-shop-economics`)
- [ ] ⚠️ **TSBs and recalls checked** (§25 → `car-diagnostic-method-obd-tools-and-shop-economics`)
- [ ] Freeze frame captured before clearing anything (§26 → `car-diagnostic-method-obd-tools-and-shop-economics`)
- [ ] ⚠️ **Visual inspection done — wiring, connectors, leaks** (§25 → `car-diagnostic-method-obd-tools-and-shop-economics`)
- [ ] ⚠️ **A TEST performed that distinguishes this cause from the alternatives**
- [ ] ⚠️ **Root cause identified, not just the failed component** (§26 → `car-diagnostic-method-obd-tools-and-shop-economics`)
- [ ] Relearn/calibration requirements known before starting (§6 → `car-engine-cycle-fuel-ignition-management-and-emissions`, §18 → `car-electrical-networks-adas-ev-and-high-voltage-safety`)
- [ ] ⚠️ **Fix verified under the original failing conditions** (§25 → `car-diagnostic-method-obd-tools-and-shop-economics`)

---
