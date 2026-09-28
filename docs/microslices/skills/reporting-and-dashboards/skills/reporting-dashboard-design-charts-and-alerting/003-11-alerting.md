---
id: skill-11-alerting-cb1cafe075
purpose: 11 alerting
source: src/vibey_tools/skills/plugins/reporting-and-dashboards/skills/reporting-dashboard-design-charts-and-alerting/SKILL.md
requires: ["skill-10-chart-selection-03668a9586"]
links: []
---

## §11. Alerting

**⚠️ Alerting is where reporting becomes operational, and the failure mode is fatigue.**
**Threshold** (simple, brittle), **relative change**, **statistical/anomaly** (⚠️ **must
account for seasonality — Monday is not Sunday, and December is not November**),
**forecast-band**.
**⚠️ Rules that keep alerting useful**: **every alert names an action**; **route to someone
specific**; **suppress duplicates and storms**; ⚠️ **and delete alerts that are routinely
ignored — an ignored alert is worse than none, because it trains people to ignore the
channel.** **Data-quality alerts (freshness, volume, null rate, schema change) usually
matter more than metric alerts** (§14 → `reporting-access-control-embedded-and-testing`).
