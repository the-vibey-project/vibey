---
id: skill-29-what-s-live-verified-august-2026-6ee4e49644
purpose: 29 what s live verified august 2026
source: src/vibey_tools/skills/plugins/thermodynamics-fluid-mechanics/skills/thermo-reference/SKILL.md
requires: []
links: ["skill-30-anti-patterns-dd7d5f06db"]
---

## §29. What's Live — verified August 2026

### 29.1 ⚠️ CFD: GPUs moved the boundary, ML has not replaced the models
**⚠️ The physics didn't change; what you can afford to compute did.**

- **⚠️ RANS remains dominant in industry, and the sources are blunt about why.**
  ⚠️ **Scale-resolving methods remain "computationally infeasible for most industrial CFD
  practitioners," and RANS is projected to stay the most common approach for the near
  future.** **The reason is §22 → `thermo-dimensional-analysis-flows-turbulence-and-turbomachinery`'s Re³ scaling — DNS at industrial Reynolds numbers is
  described as out of reach "for decades."**
- **⚠️ GPU acceleration is the real, deployed change.** **OpenFOAM with GPU backends,
  Ansys Fluent GPU acceleration and GPU-native solvers are reported achieving
  10–100× speedups over CPU-only runs**, ⚠️ **progressively making LES accessible for a
  broader range of industrial problems.** **A NASA seminar description put it as GPU
  hardware having "initiated a transition from classical RANS-based methods to
  Scale-Resolving Simulation approaches" in external aerodynamics.**
- **⚠️ ML in turbulence modelling is genuinely promising and genuinely not there yet.**
  ⚠️ **One 2026 assessment: hybrid physics-ML turbulence models are "still largely in the
  research phase" and likely to enter mainstream industrial tools "within the next 5–10
  years," with the most promising near-term application being data-driven RANS correction
  for separated flows — where classical RANS is known to be systematically wrong.**
- **⚠️ The theoretical obstacle is real, not just engineering lag.** **Research reports
  non-unique ML mappings in data-driven RANS models, difficulty achieving robust
  generalization, and accumulated industrial evidence suggesting "a universal, simple, and
  local turbulence model may be difficult to achieve."**

> **⚠️ GOTCHA — read "1000× faster" claims carefully, and note what they're measuring.**
> ⚠️ **Headline speedups typically describe SURROGATE MODELS trained on prior CFD results,
> not solvers.** **A surrogate interpolates within its training distribution; it does not
> solve Navier-Stokes, and it has no reliable error bound outside that distribution.**
> **⚠️ That's genuinely useful for design-space exploration and dangerous as a
> verification tool.** ⚠️ **Also note where the credible deployment actually is —
> astronomy adaptive optics and long-range imaging, per one 2026 survey — rather than in
> certified aerodynamic design.**

**⚠️ The practitioner summary**: ⚠️ **use RANS for design iteration, know its failure modes
(separation, strong curvature, rotation — §22 → `thermo-dimensional-analysis-flows-turbulence-and-turbomachinery`'s Boussinesq problem), reach for
scale-resolving methods where those failures matter and GPUs make it affordable, and treat
ML surrogates as fast interpolators rather than as solvers.** **⚠️ Validation against
experiment did not become less necessary.**

### 29.2 ⚠️ High-density thermal management: air hit a wall
**⚠️ The most consequential applied heat-transfer problem right now, and it is §26 → `thermo-heat-transfer-conduction-convection-radiation-and-exchangers`'s
h-magnitude table becoming a business constraint.**

- **⚠️ The physical driver: liquid's volumetric heat transfer capacity is roughly
  3,000–4,000× that of air.** ⚠️ **Air cooling reaches physical limits reported around
  25–50 kW per rack depending on layout** — **and modern accelerator racks blow past it.**
  **An NVIDIA GB200 NVL72 is reported drawing roughly 120 kW, with GB300 configurations
  pushing 135–200 kW.** ⚠️ **Chip TDPs exceeding 1,000 W today are projected toward
  4,000 W by 2029.**
- **⚠️ The threshold framework that recurs across sources**: **below ~20–30 kW/rack air
  with rear-door heat exchangers remains defensible; ⚠️ 20–50 kW is the direct-to-chip
  zone (ASHRAE TC 9.9 recommends DLC above 20 kW, and one source notes this is "grounded
  in heat flux physics, not vendor preference"); above ~50 kW liquid is mandatory; above
  ~100 kW immersion enters.**
- **⚠️ Direct-to-chip cold plates dominate** — **reported at roughly 65% of the liquid
  cooling market in 2026, and expected to remain dominant through at least 2028 because
  they are mature, retrofittable, and what the hardware vendors specify.**
  ⚠️ **Immersion achieves the best PUE (reported 1.02–1.05) and carries real
  compatibility problems: elastomer seals degrading, thermal interface materials
  dissolving, conformal coatings reacting.**

> **⚠️ GOTCHA — the most thermodynamically interesting development is the warm-water
> move, and it's a §4 → `thermo-laws-entropy-property-relations-and-phase-behaviour` argument.** ⚠️ **NVIDIA's Vera Rubin is specified for single-phase
> direct liquid cooling at a 45°C supply temperature** — **high enough that data centres
> can reject heat through DRY COOLERS using ambient air rather than mechanical chillers.**
> **⚠️ Chillers are among the largest energy draws in a liquid-cooled facility, so raising
> the coolant temperature eliminates an entire refrigeration cycle.** ⚠️ **This is
> exactly §10 → `thermo-cycles-exergy-combustion-and-psychrometrics`'s exergy lesson in practice: don't spend work moving heat down a temperature
> gradient you didn't need to create.**

**⚠️ Adoption figures vary widely by source and should be treated as directional** —
**one puts liquid cooling in new builds at ~22% in 2026, another projects ~37% penetration
against ~3% in 2021.** ⚠️ **Average rack density was reported jumping 69% year-over-year to
about 27 kW, with AI training racks as the outliers pulling the average up.**
**⚠️ And the honest closing note from one industry source, which is a systems point rather
than a chip point**: ⚠️ **"The chip-level thermal problem is solved. The building-level and
community-level thermal problems are just getting started"** — **heat rejection capacity,
water availability and permitting are the actual bottlenecks.** **⚠️ Two-phase immersion
additionally faces fluid-availability and PFAS regulatory risk.**

---
