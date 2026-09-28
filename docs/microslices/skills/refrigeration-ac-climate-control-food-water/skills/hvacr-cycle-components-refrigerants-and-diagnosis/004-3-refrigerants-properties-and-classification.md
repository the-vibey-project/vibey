---
id: skill-3-refrigerants-properties-and-classification-4854506300
purpose: 3 refrigerants properties and classification
source: src/vibey_tools/skills/plugins/refrigeration-ac-climate-control-food-water/skills/hvacr-cycle-components-refrigerants-and-diagnosis/SKILL.md
requires: ["skill-2-components-5120f88214"]
links: ["skill-4-charge-evacuation-and-leaks-3e9e5ac36a"]
---

## §3. ⚠️ Refrigerants — Properties and Classification

```
⚠️ NAMING  R-<number>. ⚠️ 400-series = ZEOTROPIC blends (components boil at
   different temperatures → GLIDE); 500-series = azeotropic;
   ⚠️ 600-series = organics (R-600a isobutane); 700-series = inorganic
   (R-717 ammonia, R-718 water, R-744 CO₂); ⚠️ R-1234xx = HFOs
⚠️ ASHRAE 34 SAFETY CLASSES
   TOXICITY  A (lower) · B (higher — ⚠️ ammonia is B)
   FLAMMABILITY  1 (none) · 2L (⚠️ MILDLY flammable, burning velocity
      <10 cm/s) · 2 (flammable) · 3 (⚠️ higher flammability — propane)
   ⚠️ So: R-410A = A1 · R-32 and R-454B = A2L · R-290 propane = A3 ·
      R-717 ammonia = B2L
⚠️ ODP  ozone depletion — CFCs and HCFCs, addressed by Montreal Protocol
⚠️ GWP  global warming potential — HFCs, addressed by Kigali/AIM/F-Gas (§25.1)
⚠️ GLIDE  ⚠️ zeotropic blends change temperature as they evaporate, which
   means you MUST charge them as LIQUID and cannot top up after a leak
   without risking fractionation
```
> **⚠️ GOTCHA — you cannot "drop in" a different refrigerant.** ⚠️ **Pressure-temperature
> relationships, oil compatibility (mineral oil for CFC/HCFC, POE for HFC/HFO), material
> compatibility, metering device sizing and system safety design all differ.** **⚠️ Putting
> an A2L into a system not designed and certified for it is unsafe and generally illegal
> — the equipment needs leak detection, specific electrical design, and charge limits per
> UL 60335-2-40** (§25.1 → `hvacr-reference`).

**⚠️ Natural refrigerants have real advantages and real constraints**: ⚠️ **CO₂ (R-744) is
non-toxic and non-flammable with negligible GWP but runs at very high pressure and goes
TRANSCRITICAL above ~31°C, which hurts efficiency in hot climates; ammonia (R-717) is the
most thermodynamically efficient common refrigerant and is toxic, so it's confined to
industrial plant with trained operators; propane (R-290) is excellent and flammable, so
it's limited to small sealed charges.**

---
