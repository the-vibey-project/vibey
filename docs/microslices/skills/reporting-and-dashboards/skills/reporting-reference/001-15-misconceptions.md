---
id: skill-15-misconceptions-9950dc90c3
purpose: 15 misconceptions
source: src/vibey_tools/skills/plugins/reporting-and-dashboards/skills/reporting-reference/SKILL.md
requires: []
links: ["skill-16-what-moved-verified-august-2026-b3232ed4e3"]
---

## §15. Misconceptions

| Misconception | Correction |
|---|---|
| A successful query means a correct number | ⚠️ **Analytics fails silently. That's the core problem** (§0 → `reporting-architecture-modelling-and-aggregation-traps`, §3 → `reporting-architecture-modelling-and-aggregation-traps`) |
| Joining tables then summing is fine | ⚠️ **Fan-out multiplies your measures** (§3.1 → `reporting-architecture-modelling-and-aggregation-traps`) |
| You can join two fact tables via a dimension | ⚠️ **Cartesian product. Aggregate separately** (§3.2 → `reporting-architecture-modelling-and-aggregation-traps`) |
| All measures can be summed | ⚠️ **Semi-additive and non-additive measures exist** (§3.3 → `reporting-architecture-modelling-and-aggregation-traps`) |
| Average the regional conversion rates | ⚠️ **Recompute from components. Averages of ratios are wrong** (§3.3 → `reporting-architecture-modelling-and-aggregation-traps`) |
| Distinct counts roll up | ⚠️ **They don't. Recompute or use HLL** (§3.4 → `reporting-architecture-modelling-and-aggregation-traps`) |
| If every segment improves, the total improves | ⚠️ **Simpson's paradox** (§4 → `reporting-architecture-modelling-and-aggregation-traps`) |
| The average is a useful summary | ⚠️ **For skewed data, use percentiles** (§4 → `reporting-architecture-modelling-and-aggregation-traps`) |
| A metric target is a good measure | ⚠️ **Goodhart's law** (§4 → `reporting-architecture-modelling-and-aggregation-traps`) |
| Store timestamps in local time | ⚠️ **UTC, convert at presentation — but ask whose day it is** (§6 → `reporting-semantic-layer-time-and-performance`) |
| A day is 24 hours | ⚠️ **Not across a DST boundary** (§6 → `reporting-semantic-layer-time-and-performance`) |
| ISO week 1 is the first week of January | ⚠️ **It contains the first Thursday** (§6 → `reporting-semantic-layer-time-and-performance`) |
| MTD vs last month is a fair comparison | ⚠️ **8 days vs 30. The most common dashboard lie** (§6 → `reporting-semantic-layer-time-and-performance`) |
| Yesterday's number is final | ⚠️ **Late-arriving data. State a completeness window** (§6 → `reporting-semantic-layer-time-and-performance`) |
| Type 1 SCD is the simple default | ⚠️ **It silently rewrites history** (§2 → `reporting-architecture-modelling-and-aggregation-traps`) |
| Slow dashboard means a bigger warehouse | ⚠️ **Check partition pruning first** (§7 → `reporting-semantic-layer-time-and-performance`) |
| Real-time is better | ⚠️ **Usually unnecessary and an order of magnitude more expensive** (§8 → `reporting-semantic-layer-time-and-performance`) |
| Logic in the BI tool is fine for now | ⚠️ **Invisible, untested, and it's how definitions diverge** (§1 → `reporting-architecture-modelling-and-aggregation-traps`, §5 → `reporting-semantic-layer-time-and-performance`) |
| Truncating the y-axis is a style choice | ⚠️ **On bar charts it misrepresents by construction** (§10 → `reporting-dashboard-design-charts-and-alerting`) |
| Pie charts are fine for comparison | ⚠️ **Angle ranks poorly perceptually. Use bars** (§10 → `reporting-dashboard-design-charts-and-alerting`) |
| A choropleth of counts shows activity | ⚠️ **It shows population. Normalize** (§10 → `reporting-dashboard-design-charts-and-alerting`) |
| A dashboard filter enforces access | ⚠️ **Trivially bypassed. Enforce server-side** (§12 → `reporting-access-control-embedded-and-testing`, §13 → `reporting-access-control-embedded-and-testing`) |
| Schema tests cover analytics correctness | ⚠️ **A fan-out bug passes all of them. Reconcile to source** (§14 → `reporting-access-control-embedded-and-testing`) |
| More dashboards means more insight | ⚠️ **Most are never opened** (§9 → `reporting-dashboard-design-charts-and-alerting`) |
| Natural language querying has solved BI | ⚠️ **Enterprise accuracy is far below benchmark headlines** (§16.2) |

---
