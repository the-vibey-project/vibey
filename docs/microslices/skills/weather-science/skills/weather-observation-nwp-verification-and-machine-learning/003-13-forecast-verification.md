---
id: skill-13-forecast-verification-3cdc572a23
purpose: 13 forecast verification
source: src/vibey_tools/skills/plugins/weather-science/skills/weather-observation-nwp-verification-and-machine-learning/SKILL.md
requires: ["skill-12-numerical-weather-prediction-23f2b2eb55"]
links: ["skill-14-predictability-and-chaos-5e7e4101f4"]
---

## §13. Forecast Verification

**⚠️ "Was the forecast good?" is a harder question than it looks, and the metric you choose
determines the answer** (§15.3).
```
RMSE / MAE                deterministic error  ⚠️ REWARDS SMOOTHING — see §15.3
ACC (anomaly correlation) ⚠️ the standard synoptic skill score; 0.6 conventionally
                          taken as the limit of useful deterministic skill
Brier score               probabilistic, binary events
CRPS                      ⚠️ probabilistic, continuous — the standard ensemble metric
Reliability diagram       ⚠️ do 30% forecasts verify 30% of the time?
POD / FAR / CSI           categorical events
```
**⚠️ The double penalty problem**: a sharp forecast of a feature in slightly the wrong place
is penalized twice — **once for predicting it where it wasn't, once for missing it where it
was.** ⚠️ **A blurry forecast scores better on RMSE while being less useful.** **This is
not a technicality; it distorts model development toward smoothness** (§15.3).

**⚠️ Skill must beat a reference** — persistence, climatology, or a previous model.
**"85% accurate" means nothing without one.**

---
