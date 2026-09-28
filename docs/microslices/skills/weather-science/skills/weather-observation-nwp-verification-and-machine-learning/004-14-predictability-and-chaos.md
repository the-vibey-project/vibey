---
id: skill-14-predictability-and-chaos-5e7e4101f4
purpose: 14 predictability and chaos
source: src/vibey_tools/skills/plugins/weather-science/skills/weather-observation-nwp-verification-and-machine-learning/SKILL.md
requires: ["skill-13-forecast-verification-3cdc572a23"]
links: ["skill-15-machine-learning-weather-prediction-24aae19645"]
---

## §14. Predictability and Chaos

### 14.1 The intrinsic limit
**Lorenz (1963)** — ⚠️ **deterministic nonlinear systems exhibit sensitive dependence on
initial conditions.** Errors grow, and **small-scale errors propagate upscale.**
> **⚠️ GOTCHA — the predictability limit is a property of the atmosphere, not of our
> instruments or models.** ⚠️ **Roughly two weeks for synoptic-scale deterministic
> forecasting is a mathematical bound, not an engineering target.** **Perfect observations
> and a perfect model would not remove it** — see a Newtonian-mechanics reference §13 for
> why better data buys only logarithmic improvement.
>
> **⚠️ And predictability is flow-dependent.** Some regimes are far more predictable than
> others, which is exactly what the ensemble spread is telling you (§12.3).

**Scale matters**: convective cells minutes to hours; mesoscale systems hours; synoptic
systems days; **planetary waves and teleconnections longer.** ⚠️ **Seasonal forecasting
works not by predicting weather but by predicting boundary-condition-driven shifts in the
distribution** — chiefly ENSO (§6 → `weather-dynamics-circulation-and-synoptic`).

---
