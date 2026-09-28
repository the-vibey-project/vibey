---
id: skill-1-structure-of-the-atmosphere-fd7c2c95c3
purpose: 1 structure of the atmosphere
source: src/vibey_tools/skills/plugins/weather-science/skills/weather-atmosphere-radiation-thermodynamics-and-moisture/SKILL.md
requires: ["skill-0-routing-be8267af44"]
links: ["skill-2-radiation-and-the-energy-budget-4b686c3b3f"]
---

## §1. Structure of the Atmosphere

```
Troposphere    surface–~11 km  ⚠️ ALL weather. Temperature DECREASES with height
Tropopause     ⚠️ the lid — ~8 km polar, ~17 km tropical
Stratosphere   ~11–50 km  temperature INCREASES (ozone absorbs UV) ⚠️ → very stable
Mesosphere     ~50–85 km  decreases again
Thermosphere   >85 km     increases; extremely thin
```
**⚠️ The tropopause is a lid because the stratosphere's temperature inversion makes it
strongly stable** — rising air becomes colder than its surroundings and stops.
**This is why thunderstorm anvils spread horizontally**, and why weather is confined to the
lowest ~10 km.

**Composition**: N₂ 78%, O₂ 21%, Ar 0.93%, CO₂ ~0.04% and rising, **water vapour 0–4% and
highly variable** — ⚠️ **water vapour is the variable one, and its variability is most of
what makes weather.**

**Hydrostatic balance** — ⚠️ **the single most important approximation in meteorology:**
```
dP/dz = −ρg
```
**The upward pressure-gradient force balances gravity.** ⚠️ **Excellent to within a
fraction of a percent for large-scale flow, and it fails only in deep convection** — which
is exactly why convection-resolving models must be **non-hydrostatic** (§12.1 → `weather-observation-nwp-verification-and-machine-learning`).
**Scale height** ≈ 8 km — pressure falls roughly exponentially, halving about every 5.5 km.

---
