---
id: skill-6-engine-management-and-closed-loop-control-436f37558f
purpose: 6 engine management and closed loop control
source: src/vibey_tools/skills/plugins/how-cars-work-and-how-mechanics-work/skills/car-engine-cycle-fuel-ignition-management-and-emissions/SKILL.md
requires: ["skill-5-ignition-and-knock-d8530843eb"]
links: ["skill-7-cooling-and-lubrication-15ffd9790b"]
---

## §6. ⚠️ Engine Management and Closed-Loop Control

**⚠️ Understand this and most driveability diagnosis becomes readable.**
```
⚠️ THE ECU'S JOB  maintain the air-fuel ratio near STOICHIOMETRIC
   (~14.7:1 for petrol) because ⚠️ THE CATALYST ONLY WORKS THERE (§8)
⚠️ THE FEEDBACK LOOP
   ⚠️ Upstream O2 / wideband sensor reads exhaust oxygen
   → ECU adjusts injector pulse width
   → ⚠️ SHORT TERM FUEL TRIM (STFT) swings moment to moment
   → ⚠️ LONG TERM FUEL TRIM (LTFT) learns the persistent correction
⚠️ READING TRIMS IS THE CORE SKILL
   ⚠️ POSITIVE trim = ECU ADDING fuel = it sees LEAN
   ⚠️ NEGATIVE trim = ECU REMOVING fuel = it sees RICH
   ⚠️ Lean at IDLE but fine at load → vacuum leak (leak is a fixed
      volume, proportionally huge at idle)
   ⚠️ Lean at LOAD but fine at idle → fuel delivery or a MAF reading low
   ⚠️ Lean on ONE BANK only → that bank's O2, injectors, or a
      bank-specific leak — NOT the fuel pump
```
**⚠️ Open loop vs closed loop**: ⚠️ **cold start, wide-open throttle and some failure modes
run OPEN loop from a table, ignoring the O2 sensor** — **which is why some faults only
appear once the engine warms and closes the loop.**
**⚠️ Adaptations and relearns**: ⚠️ **the ECU learns; after a repair, learned corrections
may need clearing, and throttle bodies, transmissions and steering angle sensors often
require explicit relearn procedures** (§27 → `car-diagnostic-method-obd-tools-and-shop-economics`).

---
