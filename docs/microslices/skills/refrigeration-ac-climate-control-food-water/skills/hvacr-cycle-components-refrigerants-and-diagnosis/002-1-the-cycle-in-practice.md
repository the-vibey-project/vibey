---
id: skill-1-the-cycle-in-practice-ebd45501e3
purpose: 1 the cycle in practice
source: src/vibey_tools/skills/plugins/refrigeration-ac-climate-control-food-water/skills/hvacr-cycle-components-refrigerants-and-diagnosis/SKILL.md
requires: ["skill-0-routing-edb4b7e311"]
links: ["skill-2-components-5120f88214"]
---

## §1. The Cycle in Practice

```
⚠️ COMPRESSOR   low-pressure vapour → high-pressure, high-temperature vapour
⚠️ CONDENSER    rejects heat; vapour → liquid (⚠️ and SUBCOOLS below
                saturation before leaving)
⚠️ METERING     expansion valve or capillary — pressure drops, some liquid
                flashes to vapour and the mixture gets COLD
⚠️ EVAPORATOR   absorbs heat; liquid → vapour (⚠️ and SUPERHEATS above
                saturation before returning)
```
**⚠️ The idea most people miss**: ⚠️ **the cold does not come from the compressor.** **It
comes from LATENT HEAT of vaporization in the evaporator — the refrigerant boils, and
boiling absorbs enormous energy at constant temperature.** ⚠️ **The compressor's job is to
raise the pressure so the vapour can be condensed at ambient temperature; it's a pump for
the cycle, not a cold generator.**
**⚠️ Why the expansion device is deliberately wasteful**: ⚠️ **throttling is isenthalpic and
irreversible — a turbine could recover work but isn't worth the complexity at small
scale.** **This is one of the largest single sources of inefficiency in the cycle and it's
accepted on cost grounds.**

---
