---
id: skill-3-thermodynamics-and-stability-9b4b3a7b25
purpose: 3 thermodynamics and stability
source: src/vibey_tools/skills/plugins/weather-science/skills/weather-atmosphere-radiation-thermodynamics-and-moisture/SKILL.md
requires: ["skill-2-radiation-and-the-energy-budget-4b686c3b3f"]
links: ["skill-4-moisture-and-clouds-2317e5b3cc"]
---

## §3. Thermodynamics and Stability

**Adiabatic processes** — no heat exchange, so rising air expands and cools by doing work
on its surroundings.
```
Dry adiabatic lapse rate (DALR)     ⚠️ 9.8 °C/km — a constant, from physics
Saturated adiabatic lapse rate      ⚠️ ~4–7 °C/km — LESS, because condensation
                                    releases latent heat that partly offsets cooling
Environmental lapse rate (ELR)      ⚠️ whatever the actual sounding says — measured
Standard atmosphere average         6.5 °C/km
```
> **⚠️ GOTCHA — stability is a COMPARISON between the parcel's lapse rate and the
> environment's, not a property of either alone.**
> ```
> ELR < SALR           absolutely stable    ⚠️ parcel always colder → sinks back
> SALR < ELR < DALR    conditionally unstable ⚠️ stable if dry, unstable if saturated
>                      — and this is the common atmospheric state
> ELR > DALR           absolutely unstable  ⚠️ rare and short-lived; convection
>                      destroys it immediately
> ```
> **⚠️ "Conditionally unstable" is the key state: the atmosphere is often stable to dry
> displacement and unstable once a parcel saturates.** **That's why you need a trigger to
> get a thunderstorm even when the environment is primed** (§8 → `weather-severe-storms-cyclones-and-boundary-layer`).

**Potential temperature `θ`** — the temperature a parcel would have if brought
adiabatically to 1000 hPa. ⚠️ **Conserved under dry adiabatic motion, which makes it the
natural vertical coordinate for tracking air masses.** **`θ_e` (equivalent potential
temperature)** is conserved including moisture, and is the workhorse variable.

**CAPE / CIN** — ⚠️ **CAPE (Convective Available Potential Energy) is the integrated
buoyancy available to a rising parcel, in J/kg — it's the fuel.** **CIN (Convective
Inhibition) is the energy barrier that must be overcome first — it's the lid.**
⚠️ **High CAPE with strong CIN means nothing happens until something breaks the cap — and
then everything happens at once.** **This is why the most violent storms often form in
capped environments.**

---
