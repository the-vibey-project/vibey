---
id: skill-4-metric-definition-pitfalls-c5891211cc
purpose: 4 metric definition pitfalls
source: src/vibey_tools/skills/plugins/reporting-and-dashboards/skills/reporting-architecture-modelling-and-aggregation-traps/SKILL.md
requires: ["skill-3-the-aggregation-traps-6b8b4375cd"]
links: []
---

## §4. Metric Definition Pitfalls

**⚠️ Simpson's paradox** — a trend present in every subgroup can reverse in the aggregate.
⚠️ **This is not a curiosity; it happens in real business data whenever group sizes shift.**
**A treatment can improve outcomes for every segment while appearing to worsen results
overall, because the mix changed.** **The defence is to always be able to decompose a
metric by its main dimensions, and to be suspicious when an aggregate moves against all
its parts.**

**⚠️ Other definitional traps:**
- **Numerator/denominator mismatch** — ⚠️ **counting conversions over a different window
  or population than visits. Extremely common and rarely noticed.**
- **Survivorship** — ⚠️ **"average customer lifetime" computed only over churned customers
  is systematically wrong.**
- **Cohort vs snapshot** — "retention" means different things, and both are legitimate.
  ⚠️ **Say which.**
- **⚠️ Attribution** — first-touch, last-touch, linear, time-decay all give different
  answers from identical data, and **none is objectively correct.**
- **Active user** — ⚠️ **daily/weekly/monthly, what counts as activity, whether bots and
  internal users are excluded.** **Define it in writing.**
- **⚠️ Averages hide distributions.** **Report percentiles for anything latency-like or
  skewed. p50 and p95 tell you more than a mean, and a mean of a long-tailed distribution
  is close to meaningless.**
- **Goodhart's law** — ⚠️ **any metric used as a target ceases to be a good measure.**
  **Expect the metric to be optimized, sometimes destructively, and instrument the thing
  it's a proxy for.**
