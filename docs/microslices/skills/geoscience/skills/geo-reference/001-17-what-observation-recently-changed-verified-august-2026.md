---
id: skill-17-what-observation-recently-changed-verified-august-2026-9368c67b72
purpose: 17 what observation recently changed verified august 2026
source: src/vibey_tools/skills/plugins/geoscience/skills/geo-reference/SKILL.md
requires: []
links: ["skill-18-misconceptions-c6b4d1624e"]
---

## §17. What Observation Recently Changed — verified August 2026

### 17.1 ⚠️ Satellite gravimetry and continental drying
**GRACE and GRACE-FO measure the mass of water by its gravitational signal** — ⚠️ **a
genuinely new observational capability that lets us weigh continental water storage
directly rather than infer it.**

**The findings, from peer-reviewed work:**
- **⚠️ A Science Advances study reports unprecedented terrestrial water storage loss since
  2002**, with **areas experiencing drying increasing by twice the size of California
  annually** (~831,600 km²/yr), forming **"mega-drying" regions across the Northern
  Hemisphere.**
- **⚠️ Groundwater depletion accounts for 68% of terrestrial water storage loss over
  non-glaciated continental regions.**
- **⚠️ Dry areas are now drying faster than wet areas are wetting** — which is not what a
  simple "wet gets wetter" framing predicts.
- **⚠️ The continents now contribute more freshwater to sea level rise than the ice
  sheets**, and drying regions contribute more than glaciers and ice caps. **That
  reframes the sea level budget.**
- **75% of the population lives in 101 countries that have been losing freshwater.**
- **A separate GRACE/GRACE-FO analysis over 21.5 years** finds **groundwater depletion
  dominating freshwater decline at continental scales, most prominently in Asia at
  −55 km³/yr**, ⚠️ **while ice mass loss remains the largest single global contributor by
  component** — **and it identifies emerging groundwater *gains* in some regions
  alongside widespread decline.**
- **NASA reports 21 of Earth's 37 largest aquifers have exceeded sustainability tipping
  points, 13 of them significantly distressed.**

> **⚠️ GOTCHA — GRACE is powerful and it has real uncertainties, and the literature is
> explicit about this.** ⚠️ **Groundwater storage is not measured directly — it's derived
> by subtracting modelled soil moisture, snow, surface water and glacier contributions
> from total water storage, so model error propagates in.** **A published re-analysis
> found earlier GRACE-based depletion rates for the Northwest India Aquifer were likely
> overestimates**, with constrained forward modelling giving **~14 km³/yr against a
> published ~18 km³/yr** — and the corrected figure matched well-monitoring data.
> ⚠️ **Where GRACE has been compared against dense well networks it generally agrees
> (correlations ~0.52–0.95 across major US aquifers), which is the reassuring part — but
> treat single-basin headline numbers with more caution than continental-scale trends.**

**⚠️ Why this belongs in a geoscience document rather than a news summary**: it is a
**measurement capability change**, not a policy story. **We can now weigh the continents'
water, and the answer differed from what models assumed.**

### 17.2 ⚠️ Deep learning in seismology
**A quieter revolution, and it changed what the observational record contains.**

**The problem it solved**: ⚠️ **STA/LTA detection had been the backbone of real-time
seismic processing since the earliest digital acquisition, and manual picking by skilled
analysts had become impossible to scale as channel counts grew.**

**The models**: **PhaseNet** (⚠️ **Zhu & Beroza 2019 — a U-Net that reformulates phase
picking as image segmentation**), **EQTransformer** (⚠️ **Mousavi et al. 2020 — CNN +
LSTM + self-attention doing joint detection and picking, and notably compact at ~379k
parameters**), **GPD**, and association methods like **GaMMA**.

**⚠️ The consequence for the science, which is the important part**: **these models detect
earthquakes missed by standard methods**, and the resulting catalogues have
⚠️ **contributed to uncovering fault-structure complexity and earthquake swarm dynamics,
giving new insight into aseismic crustal processes.** **One 2026 study applying a DL
workflow to a single day containing a major mainshock obtained 5,315 earthquakes — reduced
to 3,839 after location-quality filtering — against 1,086 in the manually reviewed
catalogue.** ⚠️ **The record got several times denser, and denser catalogues change what
questions you can ask.**

**⚠️ DAS is the amplifier.** **PhaseNet-DAS** applies this to fibre-optic distributed
acoustic sensing, ⚠️ **turning existing telecom cable into an ultra-dense seismic array.**
The scale is different in kind: **applied to ~9,839 catalogued earthquakes near one array,
it produced ~36 million P-picks and ~53 million S-picks.** **Submarine and ocean-bottom
variants (DeepSubDAS, PickBlue, OBSTransformer) extend it to marine environments** —
⚠️ **which matters because seismometers are scarce at sea and most plate boundaries are
underwater.**

**⚠️ The honest caveats, and the literature is candid**: models trained on regional surface
stations at 100 Hz ⚠️ **transfer poorly to high-frequency borehole data (2000 Hz) and to
DAS without retraining**; there is documented **prediction inconsistency and parameter
dependence** in neural pickers, with active work on mitigation; and ⚠️ **catalogue
performance is variable enough that a 2026 paper is titled, in effect, "which is better:
deep learning or manual picking?"** — **it is not a settled rout.**

---
