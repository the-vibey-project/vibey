---
id: skill-5-the-semantic-layer-d355433096
purpose: 5 the semantic layer
source: src/vibey_tools/skills/plugins/reporting-and-dashboards/skills/reporting-semantic-layer-time-and-performance/SKILL.md
requires: []
links: ["skill-6-time-handling-b541e8aed2"]
---

## §5. The Semantic Layer

**⚠️ The problem it solves is organizational, not technical**: **without one, metric logic
is duplicated into every dashboard, notebook, spreadsheet and application** — ⚠️ **and
duplicated logic diverges, so two directors arrive at a meeting with different revenue
numbers and the meeting becomes about the numbers.**

**A semantic layer defines entities, dimensions and metrics once, and compiles them to
SQL on demand.**
```
Entities/models   the tables and their keys
Dimensions        what you group and filter by
Measures/metrics  ⚠️ the aggregation logic, defined ONCE
Joins             ⚠️ declared with cardinality, so the tool can avoid §3.1
```
**⚠️ Declared join cardinality is the underrated feature.** **It's what lets the layer
apply symmetric aggregates and avoid fan-out automatically** — **a class of bug removed by
construction rather than by vigilance.**

**⚠️ What it buys**: one definition, governed access, consistent results across BI tools
and notebooks and APIs, version control and code review for business logic, and
⚠️ **a stable target for AI agents that would otherwise be querying raw tables** (§16 → `reporting-reference`).
**⚠️ What it costs**: another abstraction, a modelling language to learn, a query-
compilation step to debug, and **an adoption problem — a definition nobody owns or reviews
is no better than no definition.**

---
