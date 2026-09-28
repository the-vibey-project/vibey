---
id: skill-15-machine-learning-weather-prediction-24aae19645
purpose: 15 machine learning weather prediction
source: src/vibey_tools/skills/plugins/weather-science/skills/weather-observation-nwp-verification-and-machine-learning/SKILL.md
requires: ["skill-14-predictability-and-chaos-5e7e4101f4"]
links: ["skill-16-weather-vs-climate-81a3aa3d66"]
---

## §15. Machine Learning Weather Prediction

**⚠️ This is the section that moved, and it moved fast enough that most general knowledge
about it is out of date.** **Verified August 2026.**

### 15.1 What happened
**⚠️ One assessment frames it as the biggest methodological break in forecasting since
ensemble prediction arrived in 1992** — and that seems right. **Between November 2023 and
mid-2026, data-driven models trained on reanalysis went from research curiosities to
operational systems running alongside the physics engines they were built to challenge.**

**The models**: **FourCastNet** (NVIDIA, Fourier neural operator; later SFNO),
**Pangu-Weather** (Huawei, 3D Earth-Specific Transformer), **GraphCast** (Google DeepMind,
GNN on a multi-scale icosahedral mesh), **GenCast** (⚠️ **DeepMind, a conditional diffusion
model producing ensembles**), **AIFS** (ECMWF, GNN-transformer hybrid), **Aurora**
(Microsoft), **NeuralGCM** (hybrid), **FuXi / FengWu**, **NVIDIA Atlas**, **FGN**.

**⚠️ Operational status is the important part:**
- **ECMWF's AIFS Single has run operationally since 25 February 2025** — ⚠️ **the first
  operational ML weather system**, with a **51-member probabilistic version (AIFS-CRPS)
  following.**
- **NOAA/NWS made AI/ML models available in mid-December 2025**, including **AIGFS** and
  **HyGEFS**.
- **Google's WeatherNext** family operationalized GenCast (as WeatherNext Gen).

**⚠️ The skill claims, and they're substantiated:** GraphCast **matches or exceeds IFS HRES
on global benchmarks**; **GenCast was the first probabilistic MLWP model to significantly
outperform ECMWF's ENS at high resolution** (Nature, 2024); and by 2026 ⚠️ **ensemble
systems including GenCast and FGN have surpassed the skill of the ECMWF ensemble — the
gold standard in operational meteorology — at a small fraction of the computational
cost.**

**⚠️ The computational asymmetry is the genuinely disruptive part**: training is expensive
and one-off; **inference is seconds on a single GPU versus hours on a supercomputer.**

### 15.2 ⚠️ The limits — and there is a live scientific dispute here
> **⚠️ GOTCHA — the headline "AI beats physics" and the extremes evidence genuinely
> conflict, and you should know both sides.**
>
> **A Science Advances paper (2026, Zhang et al.) found that for record-breaking weather
> extremes, ECMWF's HRES still consistently outperforms GraphCast, Pangu-Weather and FuXi**
> — ⚠️ **with AI errors larger for record-breaking heat, cold and wind across nearly all
> lead times, systematic underestimation of both frequency and intensity of records, and
> growing bias the further the record is exceeded.** ⚠️ **The performance gap was widest
> at SHORT lead times.**
>
> **The proposed mechanism is important**: ⚠️ **models trained on 1979–2017 tend to be
> limited to extreme values already observed, "as if they had an implicit ceiling," while
> physics-based models are not so constrained and can in principle represent unprecedented
> situations.**

**Other documented limitations:**
- **⚠️ Smoothing.** Models trained to minimize average error produce **overly smooth
  fields, blurring small-scale structure and systematically underrepresenting extremes,
  worsening with lead time.** ⚠️ **This is §13's double-penalty problem expressed as a
  training objective.** **Diffusion-based ensembles (GenCast) substantially address it** —
  which is a large part of why they work.
- **⚠️ Dependence on physics-based assimilation.** **Every current ML model relies on a
  conventional analysis for initial conditions** (§12.2). ⚠️ **The replacement narrative is
  oversold and the dependency is underreported** — and **GraphCast initialized on GFS
  rather than ERA5 produces systematic inconsistencies.** **ML-based data assimilation is
  the live frontier that would close this.**
- **Physical consistency** — ⚠️ **outputs can violate known physical laws or expected
  statistical consistency**, and one assessment concluded AI models **do not properly
  reproduce sub-synoptic and mesoscale phenomena.**
- **Precipitation** — ⚠️ **persistent difficulty with light precipitation across GraphCast,
  Pangu, FuXi and CREDIT, with a positive frequency bias in the drizzle regime**, attributed
  to symmetric regression losses on a non-negative intermittent variable.
- **Temporal resolution** — ⚠️ **AIFS and AIGFS step every 6 hours where GFS gives hourly
  output; that matters for hurricanes and sharp fronts.**
- **Tropical cyclones** — track prediction is good; ⚠️ **intensity is uneven, with earlier
  models underestimating peak intensity and both tested models overestimating inner-core
  size. And a subtle trap: ERA5 itself underestimates peak intensity, so agreement with
  reanalysis does not imply accuracy.**
- **Climate shift** — ⚠️ **behaviour in novel climate states not represented in training
  is an open question.**
- **⚠️ Nowcasting (0–12 h) is still behind high-resolution NWP.**

**⚠️ The counterargument deserves stating fairly too**: one 2026 review argues it is
**"certainly an over-statement to say that they can only predict what has been seen locally
in their training dataset,"** notes that ML models have **overcome long-standing physics
model biases** such as slow tropical cyclone track bias, and points to **next-generation
models incorporating observations directly** — potentially removing the reanalysis
dependency entirely.

### 15.3 ⚠️ The metrics problem underneath the dispute
**Part of why the two camps disagree is that they're measuring different things.**
⚠️ **RMSE rewards smoothing (§13), so a model that hedges scores well on the headline
metric while underrepresenting exactly the extremes that matter operationally.** **Work on
fair comparison for extremes — weighted potential CRPS and similar — exists precisely
because the standard scores flatter the smoothing problem.**
**⚠️ When you read "AI outperforms on 90% of metrics," ask which metrics, and on what
distribution of events.**

### 15.4 The state of play
**⚠️ As of 2026, no major meteorological agency has decommissioned its NWP system.**
**ECMWF, NOAA and the Met Office all run AI models *alongside* traditional ones, not
instead of them**, with AI as one guidance product among several.
**⚠️ That is the correct read**: this is an additional, extraordinarily cheap, often more
skillful source of guidance — **not a replacement for a physics-based system that still
provides the analysis, the extremes, the physical consistency, and the fallback.**

---
