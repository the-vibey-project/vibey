---
id: skill-18-forecasting-b865482847
purpose: 18 forecasting
source: src/vibey_tools/skills/plugins/logistics-software-optimization/skills/logistics-inventory-forecasting-operations-and-solvers/SKILL.md
requires: ["skill-17-inventory-d3f15f7bcc"]
links: ["skill-19-the-landscape-0cc4cb5c6a"]
---

## §18. Forecasting

**⚠️ Keep expectations calibrated: for intermittent, lumpy SKU-level demand, sophisticated
methods frequently fail to beat simple ones.**
**Methods**: **moving average, exponential smoothing / Holt-Winters, ARIMA, Croston's
method (⚠️ specifically for intermittent demand), gradient boosting on engineered
features, and hierarchical reconciliation (⚠️ forecast at multiple levels and reconcile so
they sum consistently).**
**⚠️ The M-competitions are the honest benchmark literature here**, **and the recurring
finding is that simple methods and combinations are extremely hard to beat**, ⚠️ **with ML
methods winning mainly where there is cross-series structure to exploit.**
**⚠️ Forecast accuracy metrics**: **MAPE (⚠️ breaks on zeros and is asymmetric — a real
problem for intermittent demand), MASE (⚠️ better), RMSE, bias.** ⚠️ **Track BIAS
separately from accuracy — a consistently biased forecast is a systematically
mis-stocked warehouse, and it's invisible in symmetric error metrics.**

---

# PART III — SYSTEMS

---
