---
id: skill-1-the-architecture-ea924d1aca
purpose: 1 the architecture
source: src/vibey_tools/skills/plugins/reporting-and-dashboards/skills/reporting-architecture-modelling-and-aggregation-traps/SKILL.md
requires: ["skill-0-routing-a8d5d0d78b"]
links: ["skill-2-dimensional-modelling-0fe3e94485"]
---

## §1. The Architecture

```
Sources → INGESTION → raw/landing → TRANSFORMATION → modelled tables
  → [SEMANTIC LAYER] → BI tool / API / embedded → humans and agents
                    ↘ alerting, exports, reverse ETL
```
**⚠️ ELT beat ETL because storage got cheap and warehouses got fast**: load raw, transform
in-warehouse, keep the raw layer so you can re-derive when definitions change.
⚠️ **The ability to reprocess history after fixing a definition is worth more than the
storage it costs.**

**Layering** (medallion, or staging/intermediate/marts — the names vary and the shape
doesn't):
```
Raw/bronze     ⚠️ immutable, source-shaped, never modified
Staging/silver cleaned, typed, deduplicated, renamed to conventions
Marts/gold     ⚠️ business-shaped: facts and dimensions, or wide tables
```
**⚠️ Resist transforming in the BI tool.** **Logic in a dashboard is invisible, untested,
unversioned and unreusable** — and it's how you get six definitions of the same metric
(§5 → `reporting-semantic-layer-time-and-performance`).

---
