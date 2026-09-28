---
id: skill-26-obd-ii-and-scan-data-c8ca5df69f
purpose: 26 obd ii and scan data
source: src/vibey_tools/skills/plugins/how-cars-work-and-how-mechanics-work/skills/car-diagnostic-method-obd-tools-and-shop-economics/SKILL.md
requires: ["skill-25-diagnostic-method-0008b12339"]
links: ["skill-27-tools-4ac2bfd0f3"]
---

## §26. ⚠️ OBD-II and Scan Data

```
⚠️ DTC FORMAT  P0171 → P powertrain (B body, C chassis, U network)
   0 = generic / 1 = manufacturer-specific
   ⚠️ THE CODE NAMES A CIRCUIT OR CONDITION, NOT A FAILED PART
⚠️ WHAT P0171 ACTUALLY MEANS  "System Too Lean, Bank 1" = the ECU has
   hit its correction limit adding fuel. ⚠️ CAUSES: vacuum leak,
   dirty/failing MAF, weak fuel pump, clogged filter, restricted
   injectors, exhaust leak before the sensor, low fuel pressure.
   ⚠️ The O2 sensor is the WITNESS. Replacing it is shooting the messenger
⚠️ FREEZE FRAME  the conditions when the code SET — RPM, load,
   coolant temp, speed, trims. ⚠️ Enormously underused
⚠️ MODE $06  on-board test results with pass/fail thresholds —
   ⚠️ shows marginal-but-not-yet-failing components
⚠️ READINESS MONITORS  whether self-tests have run. ⚠️ Clearing codes
   resets them, which is why a car fails an emissions test right
   after a repair
⚠️ LIVE DATA  ⚠️ fuel trims (§6) first, always. Then MAF g/s vs
   expected, O2 activity, coolant temp, load, misfire counters
⚠️ BIDIRECTIONAL CONTROL  commanding components — ⚠️ this is what
   separates a professional tool from a code reader, and it's often
   what requires OEM software or gateway access (§30.1)
```
> **⚠️ GOTCHA — "the code says the part is bad" is the defining amateur error, and it is
> encouraged by free code-reading at parts stores whose business is selling parts.**
> ⚠️ **A P0300 random misfire can be ignition, fuel, compression, a vacuum leak, an EGR
> stuck open, or bad fuel.** ⚠️ **A P0420 catalyst efficiency code is often caused by an
> exhaust leak or an upstream fault, not a dead catalyst** — **and replacing a catalyst
> without finding what killed it just kills the new one.**

---
