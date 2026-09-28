---
id: skill-20-quick-reference-da80c0ac31
purpose: 20 quick reference
source: src/vibey_tools/skills/plugins/weather-science/skills/weather-reference/SKILL.md
requires: ["skill-19-books-329d58ab1a"]
links: ["skill-21-method-1524cfa121"]
---

## §20. Quick Reference

### 20.1 Picker
| Question | Look at |
|---|---|
| Will air rise? | ⚠️ **Compare ELR to DALR/SALR; check CAPE and CIN** (§3 → `weather-atmosphere-radiation-thermodynamics-and-moisture`) |
| Where's the wind aloft? | **Geostrophic — along the isobars** (§5.1 → `weather-dynamics-circulation-and-synoptic`) |
| Why is the jet there? | ⚠️ **Thermal wind — the temperature gradient** (§5.2 → `weather-dynamics-circulation-and-synoptic`) |
| Will a cyclone develop? | **Upper-level divergence ahead of a trough; PV thinking** (§5.3 → `weather-dynamics-circulation-and-synoptic`, §7.2 → `weather-dynamics-circulation-and-synoptic`) |
| Will storms organize? | ⚠️ **Deep-layer shear** (§8 → `weather-severe-storms-cyclones-and-boundary-layer`) |
| Will a hurricane intensify? | ⚠️ **SST, low shear, mid-level moisture** (§9 → `weather-severe-storms-cyclones-and-boundary-layer`) |
| How uncertain is this forecast? | ⚠️ **Ensemble spread — and check its calibration** (§12.3 → `weather-observation-nwp-verification-and-machine-learning`) |
| Is this forecast skillful? | ⚠️ **Against what reference, on what metric?** (§13 → `weather-observation-nwp-verification-and-machine-learning`) |
| Beyond ~2 weeks? | ⚠️ **Don't. Use statistics/teleconnections instead** (§14 → `weather-observation-nwp-verification-and-machine-learning`, §16 → `weather-observation-nwp-verification-and-machine-learning`) |
| Cheap global medium-range guidance | **ML models — with §15.2 → `weather-observation-nwp-verification-and-machine-learning`'s caveats** (§15 → `weather-observation-nwp-verification-and-machine-learning`) |
| A record-breaking extreme | ⚠️ **Trust physics-based HRES over current ML** (§15.2 → `weather-observation-nwp-verification-and-machine-learning`) |

### 20.2 Reading a forecast critically
- [ ] What's the lead time relative to the predictability limit? (§14 → `weather-observation-nwp-verification-and-machine-learning`)
- [ ] Deterministic or ensemble — and if ensemble, what's the spread? (§12.3 → `weather-observation-nwp-verification-and-machine-learning`)
- [ ] Is this a smoothed field that might be hiding an extreme? (§13 → `weather-observation-nwp-verification-and-machine-learning`, §15.3 → `weather-observation-nwp-verification-and-machine-learning`)
- [ ] Physics-based, ML, or blended — and does that matter for this event type? (§15 → `weather-observation-nwp-verification-and-machine-learning`)
- [ ] What's the reference forecast the skill claim is measured against? (§13 → `weather-observation-nwp-verification-and-machine-learning`)
- [ ] Is the hazard the headline variable, or something else (surge, rain)? (§9 → `weather-severe-storms-cyclones-and-boundary-layer`)

---
