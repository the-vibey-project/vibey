---
id: skill-19-quick-reference-bb6e6ec4cc
purpose: 19 quick reference
source: src/vibey_tools/skills/plugins/reporting-and-dashboards/skills/reporting-reference/SKILL.md
requires: ["skill-18-books-438c4b4ea3"]
links: ["skill-20-method-333bae37a2"]
---

## §19. Quick Reference

### 19.1 Picker
| Situation | Do |
|---|---|
| Modelling a new subject area | ⚠️ **Declare the grain, then star schema** (§2 → `reporting-architecture-modelling-and-aggregation-traps`) |
| Attribute changes over time | ⚠️ **SCD Type 2 unless you're sure history doesn't matter** (§2 → `reporting-architecture-modelling-and-aggregation-traps`) |
| Joining to a one-to-many | ⚠️ **Aggregate before joining** (§3.1 → `reporting-architecture-modelling-and-aggregation-traps`) |
| Two facts, one dimension | ⚠️ **Aggregate separately, then combine** (§3.2 → `reporting-architecture-modelling-and-aggregation-traps`) |
| A ratio across groups | ⚠️ **SUM(num)/SUM(denom), never AVG(ratio)** (§3.3 → `reporting-architecture-modelling-and-aggregation-traps`) |
| Distinct counts at multiple grains | ⚠️ **Recompute, or HLL if approximation is acceptable** (§3.4 → `reporting-architecture-modelling-and-aggregation-traps`) |
| Same metric in many places | ⚠️ **Semantic layer** (§5 → `reporting-semantic-layer-time-and-performance`) |
| Date arithmetic anywhere | ⚠️ **A date dimension table** (§6 → `reporting-semantic-layer-time-and-performance`) |
| Comparing an incomplete period | ⚠️ **Like-for-like, or label it unmistakably** (§6 → `reporting-semantic-layer-time-and-performance`) |
| Dashboard is slow | ⚠️ **Query plan → partition pruning → columns → pre-aggregate** (§7 → `reporting-semantic-layer-time-and-performance`) |
| Skewed data | ⚠️ **Percentiles, not the mean** (§4 → `reporting-architecture-modelling-and-aggregation-traps`) |
| Comparing categories | **Bar chart** (§10 → `reporting-dashboard-design-charts-and-alerting`) |
| Precise multi-dimensional values | ⚠️ **A table** (§10 → `reporting-dashboard-design-charts-and-alerting`) |
| Multi-tenant embedding | ⚠️ **Server-side tenant enforcement from a signed token** (§13 → `reporting-access-control-embedded-and-testing`) |
| Catching modelling errors | ⚠️ **Reconcile to the source system** (§14 → `reporting-access-control-embedded-and-testing`) |
| Evaluating a text-to-SQL tool | ⚠️ **Test on YOUR schema; check phrasing consistency** (§16.2) |

### 19.2 Pre-ship checklist
- [ ] What decision does this support? ⚠️ **If none, don't ship it** (§9 → `reporting-dashboard-design-charts-and-alerting`)
- [ ] Grain declared, and is every measure valid at it? (§2 → `reporting-architecture-modelling-and-aggregation-traps`)
- [ ] Any one-to-many joins — is fan-out handled? (§3.1 → `reporting-architecture-modelling-and-aggregation-traps`)
- [ ] Every measure classified additive / semi / non? (§3.3 → `reporting-architecture-modelling-and-aggregation-traps`)
- [ ] Ratios computed from components, not averaged? (§3.3 → `reporting-architecture-modelling-and-aggregation-traps`)
- [ ] Timezone semantics stated — whose day is it? (§6 → `reporting-semantic-layer-time-and-performance`)
- [ ] Partial periods labelled or compared like-for-like? (§6 → `reporting-semantic-layer-time-and-performance`)
- [ ] Late-arriving data policy stated, watermark shown? (§6 → `reporting-semantic-layer-time-and-performance`)
- [ ] Last-refreshed timestamp visible? (§8 → `reporting-semantic-layer-time-and-performance`)
- [ ] Every number has a comparison and a definition? (§9 → `reporting-dashboard-design-charts-and-alerting`)
- [ ] Reconciles to the source system? (§14 → `reporting-access-control-embedded-and-testing`)
- [ ] Row-level security enforced server-side, not by filter? (§12 → `reporting-access-control-embedded-and-testing`)
- [ ] Will anyone actually open this in a month? (§9 → `reporting-dashboard-design-charts-and-alerting`)

---
