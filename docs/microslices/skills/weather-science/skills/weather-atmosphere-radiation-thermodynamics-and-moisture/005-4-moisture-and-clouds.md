---
id: skill-4-moisture-and-clouds-2317e5b3cc
purpose: 4 moisture and clouds
source: src/vibey_tools/skills/plugins/weather-science/skills/weather-atmosphere-radiation-thermodynamics-and-moisture/SKILL.md
requires: ["skill-3-thermodynamics-and-stability-9b4b3a7b25"]
links: []
---

## §4. Moisture and Clouds

**Measures**: **mixing ratio** and **specific humidity** (⚠️ **conserved under
temperature change — use these for tracking**), **relative humidity** (⚠️ **a ratio to
saturation, so it changes when temperature changes even with constant moisture — which
is why RH is a poor moisture variable**), **dewpoint** (⚠️ **the good intuitive one**), and
**wet-bulb temperature.**

**⚠️ Clausius-Clapeyron**: saturation vapour pressure rises roughly exponentially with
temperature — **about 7% per °C.** ⚠️ **This is one of the most consequential numbers in
atmospheric science**: warmer air holds substantially more water, which sets the scaling
for extreme precipitation intensity.

**⚠️ Cloud formation requires condensation nuclei.** Homogeneous nucleation needs
supersaturation of several hundred percent; **with CCN present, clouds form at just over
100%.** ⚠️ **Aerosol therefore controls cloud droplet number and size, which controls
albedo and precipitation efficiency — the aerosol-cloud interaction, and the largest
uncertainty in radiative forcing.**

**Precipitation formation**, two pathways:
- **Collision-coalescence** — warm clouds, droplets growing by collision. ⚠️ **Slow;
  needs a deep warm cloud.**
- **Bergeron-Findeisen (ice process)** — ⚠️ **the dominant mechanism in mid-latitudes.**
  **Saturation vapour pressure over ice is lower than over supercooled water, so ice
  crystals grow at the expense of surrounding droplets.** **Most rain in temperate regions
  starts as snow.**
- **⚠️ Supercooled water is common** down to about −40 °C, below which homogeneous freezing
  finally occurs. **This is the aircraft icing hazard.**

**Cloud classification** by altitude and form: cirro- (high), alto- (mid), strato-
(layered), cumulo- (heaped), nimbo- (precipitating). ⚠️ **Cumulonimbus is the only cloud
that produces lightning, hail and tornadoes.**
