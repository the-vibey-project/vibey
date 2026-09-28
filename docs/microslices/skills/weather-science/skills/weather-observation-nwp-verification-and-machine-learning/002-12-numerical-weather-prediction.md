---
id: skill-12-numerical-weather-prediction-23f2b2eb55
purpose: 12 numerical weather prediction
source: src/vibey_tools/skills/plugins/weather-science/skills/weather-observation-nwp-verification-and-machine-learning/SKILL.md
requires: ["skill-11-observation-ec7d1e1c01"]
links: ["skill-13-forecast-verification-3cdc572a23"]
---

## §12. Numerical Weather Prediction

### 12.1 The governing system
**The primitive equations**: momentum (Navier-Stokes on a rotating sphere), continuity,
thermodynamic energy, the ideal gas law, and moisture conservation.
⚠️ **A coupled nonlinear PDE system with no analytic solution — so you discretize.**

**Discretization**: spectral (⚠️ **spherical harmonics — historically dominant for global
models**) or grid-point (finite difference/volume, icosahedral and cubed-sphere grids).
**Vertical coordinates**: sigma, pressure, hybrid, isentropic.
**⚠️ CFL condition constrains the timestep given grid spacing and wave speed** — **which is
why resolution is expensive: halving grid spacing roughly costs 8–16×.**
**Hydrostatic** for coarse global models; ⚠️ **non-hydrostatic required below ~10 km grid
spacing, where convection begins to be resolved** (§1 → `weather-atmosphere-radiation-thermodynamics-and-moisture`).

**⚠️ Parameterization is where the physics that can't be resolved lives**: convection,
cloud microphysics, radiation, boundary layer turbulence, gravity wave drag, land surface.
⚠️ **This is the largest source of model error and the hardest part of NWP.** **The
"grey zone" — grid spacings around 1–10 km where convection is partly resolved and partly
parameterized — is genuinely awkward.**

### 12.2 ⚠️ Data assimilation — the underrated half
**The forecast is only as good as its initial conditions, and observations are sparse,
irregular and noisy.** **DA combines a short-range forecast (the "background") with
observations, weighted by their respective error statistics**, to produce an **analysis**.

**Methods**: 3D-Var, **4D-Var** (⚠️ **assimilates over a time window, using the model
itself as a constraint — ECMWF's long-standing strength**), **EnKF** (flow-dependent
error covariances from an ensemble), and **hybrid** approaches which now dominate.

> **⚠️ GOTCHA — data assimilation is arguably a larger contributor to modern forecast
> skill than model improvements, and it's almost invisible outside the field.**
> ⚠️ **It's also the reason §15's ML models are not yet a full replacement: they mostly
> consume an analysis produced by conventional physics-based assimilation.**

**Reanalysis** — ⚠️ **rerunning a fixed modern DA system over the historical record to
produce a physically consistent gridded dataset.** **ERA5 is the standard**, and it is
**the training data for essentially every ML weather model** (§15).

### 12.3 Ensembles
**⚠️ Since initial conditions and the model are both uncertain, run many forecasts.**
Perturb initial conditions (singular vectors, bred modes, EDA) and represent model
uncertainty (stochastic physics, multi-model, multi-physics).
**⚠️ Ensemble prediction arrived operationally in 1992 and was the previous methodological
break in forecasting** — before §15. **The ensemble mean is more skillful than any member;
the spread is the uncertainty estimate.**
⚠️ **A well-calibrated ensemble's spread should match its error. Under-dispersion is the
common failure and it makes forecasts overconfident.**

---
