---
id: skill-11-observation-ec7d1e1c01
purpose: 11 observation
source: src/vibey_tools/skills/plugins/weather-science/skills/weather-observation-nwp-verification-and-machine-learning/SKILL.md
requires: []
links: ["skill-12-numerical-weather-prediction-23f2b2eb55"]
---

## §11. Observation

| System | Provides | ⚠️ Notes |
|---|---|---|
| **Surface stations / METAR** | T, Td, P, wind, visibility | Sparse and land-biased |
| **Radiosonde** | ⚠️ **The vertical profile** | ~2×/day, ~800 sites; **the backbone of upper-air truth** |
| **Weather radar** | Precipitation, ⚠️ **Doppler velocity** | **Dual-pol** distinguishes hydrometeor type |
| **Satellite — geostationary** | Continuous imagery | ⚠️ **Poor at high latitudes** |
| **Satellite — polar orbiting** | Sounding, global coverage | ⚠️ **The dominant data volume in assimilation** |
| **Aircraft (AMDAR)** | Upper-air en route | ⚠️ **Dropped sharply during COVID and measurably degraded forecasts** |
| **GNSS radio occultation** | ⚠️ **Bias-free temperature/humidity profiles** | High-value, growing |
| **Buoys, ships, profilers, lightning networks** | | |

**⚠️ Radar caveats worth knowing**: the beam rises with distance so distant echoes sample
higher altitudes; **ground clutter, anomalous propagation, bright band at the melting
level, and beam blockage** all produce artifacts. ⚠️ **Doppler measures only the radial
component of velocity** — motion across the beam is invisible.

---
