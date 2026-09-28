---
id: skill-3-power-82c4a5fb42
purpose: 3 power
source: src/vibey_tools/skills/plugins/space-exploration/skills/space-power-thermal-comms-and-navigation/SKILL.md
requires: []
links: ["skill-4-thermal-control-f8b3d24d90"]
---

## §3. Power

**[DURABLE] Solar flux scales as `1/r²`, and this single fact partitions the solar
system:**
```
Venus   0.72 AU   2,600 W/m²
Earth   1.00 AU   1,361 W/m²    (the solar constant)
Mars    1.52 AU     590 W/m²    ⚠️ 43% of Earth
Jupiter 5.20 AU      50 W/m²
Saturn  9.54 AU      15 W/m²
Pluto  39.5 AU        0.9 W/m²  ⚠️ 0.07% of Earth
```
**⚠️ Solar becomes impractical roughly beyond Jupiter** — Juno flies enormous arrays at
Jupiter and is the outer limit of the approach. **Beyond that, radioisotope power is not a
preference; it's the only option.**

**Solar arrays**: triple-junction GaAs at **~30–32% efficiency**, degrading with radiation
(⚠️ **severe in Jupiter's belts and in GEO**), temperature, and dust (⚠️ **the Mars dust
accumulation that ended Opportunity and InSight**). **Always quote BOL and EOL** — the
difference can be 15–30% over a long mission.

**RTGs**: ²³⁸Pu, **87.7-year half-life**, thermoelectric conversion at only **~6–7%**
efficiency. **MMRTG ≈ 110 W electrical at BOL from ~2,000 W thermal**, decaying **~1.6%/yr**
(⚠️ **combining fuel decay and thermocouple degradation**). **⚠️ The binding constraint is
plutonium supply, not engineering** — US production restarted in 2013 at kilograms per
year, and it gates outer-planet missions.

**⚠️ The waste heat is a feature**: RTG thermal output keeps spacecraft warm in the outer
solar system, which is why RTG missions often need less dedicated survival heating.

**Batteries** (Li-ion, ~100–250 Wh/kg) size to **eclipse duration and peak load**, with
**depth-of-discharge traded against cycle life** — ⚠️ **a LEO spacecraft sees ~16
eclipses/day, so ~90,000 cycles over 15 years**, which forces shallow DoD.

**Fuel cells** for short crewed missions (⚠️ **Apollo's produced drinking water as a
by-product**), **fission** (Kilopower/KRUSTY demonstrated 1–10 kW class) for surface power
where solar duty cycle fails — ⚠️ **a lunar night is 14 Earth days, which no practical
battery bridges.**

---
