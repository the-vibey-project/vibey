---
id: skill-8-power-cycles-f575324fd6
purpose: 8 power cycles
source: src/vibey_tools/skills/plugins/thermodynamics-fluid-mechanics/skills/thermo-cycles-exergy-combustion-and-psychrometrics/SKILL.md
requires: []
links: ["skill-9-refrigeration-and-heat-pumps-2c4a00abe5"]
---

## §8. Power Cycles

```
⚠️ CARNOT     two isothermal + two isentropic. ⚠️ The efficiency ceiling,
   and impractical — the isothermal heat exchange requires infinite time
⚠️ RANKINE    steam. Pump → boiler → turbine → condenser.
   ⚠️ Improvements: superheat, reheat, regeneration (feedwater heating),
   supercritical operation. ⚠️ Condensing at low pressure is what
   makes it efficient — the vacuum matters as much as the boiler
⚠️ BRAYTON    gas turbine. Compress → burn → expand.
   ⚠️ Improvements: intercooling, reheat, regeneration.
   ⚠️ COMBINED CYCLE — Brayton exhaust feeds a Rankine bottoming cycle,
   reaching the highest efficiencies of any heat engine in service
OTTO          spark ignition. η = 1 − 1/r^(γ−1) — ⚠️ efficiency depends on
   COMPRESSION RATIO alone in the ideal case, and knock limits r
DIESEL        compression ignition; higher r, cutoff ratio penalty
STIRLING      ⚠️ external heat, regenerator, theoretically Carnot-efficient;
   practically limited by heat transfer and sealing
```
**⚠️ The universal cycle lesson**: ⚠️ **every improvement listed above is a way of moving
heat addition to a HIGHER average temperature or heat rejection to a LOWER one** —
**because §4 → `thermo-laws-entropy-property-relations-and-phase-behaviour` says that's the only lever.** **Regeneration, reheat and combined cycles are
all that one idea in different clothes.**
**⚠️ Isentropic efficiency** — **real turbines and compressors deviate from isentropic, and
⚠️ compressor irreversibility hurts more than turbine irreversibility in gas turbines
because the compressor consumes a large fraction of turbine output (the back-work ratio).**

---
