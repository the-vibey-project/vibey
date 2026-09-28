---
id: skill-14-testing-analytics-b1dc9113f1
purpose: 14 testing analytics
source: src/vibey_tools/skills/plugins/reporting-and-dashboards/skills/reporting-access-control-embedded-and-testing/SKILL.md
requires: ["skill-13-embedded-analytics-a55dbe1fb9"]
links: []
---

## §14. Testing Analytics

**⚠️ Analytics code is under-tested relative to its blast radius, and the reason is that
the failures are silent** (§0 → `reporting-architecture-modelling-and-aggregation-traps`).
```
SCHEMA/CONTRACT   ⚠️ upstream column dropped or retyped — catch at the boundary
FRESHNESS         has data arrived?
VOLUME            ⚠️ row count anomalies — a 90% drop is usually a pipeline break
UNIQUENESS        ⚠️ the primary key really is unique — this catches §3.1 at the source
NOT NULL / accepted values / referential integrity
RECONCILIATION    ⚠️ does the total match the source system? THE most valuable test
BUSINESS ASSERTIONS  revenue non-negative, percentages in [0,100], grain preserved
```
**⚠️ Reconciliation against the system of record deserves emphasis.** **It's the only test
that catches modelling errors as opposed to data errors** — **a fan-out bug passes every
schema and null test cheerfully.**

**⚠️ Practices worth adopting**: **dbt tests or equivalent in CI**, **PR review of metric
definitions like any other code**, **staging environments with production-shaped data**,
**lineage so you know what breaks when a column changes**, **and version-controlled
dashboards where the tool allows it.**
