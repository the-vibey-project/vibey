---
id: skill-7-query-performance-ddc69f6aec
purpose: 7 query performance
source: src/vibey_tools/skills/plugins/reporting-and-dashboards/skills/reporting-semantic-layer-time-and-performance/SKILL.md
requires: ["skill-6-time-handling-b541e8aed2"]
links: ["skill-8-caching-and-freshness-cc07085fc7"]
---

## §7. Query Performance

**⚠️ Columnar storage is why analytics warehouses are fast, and it dictates the tuning
rules**: only the referenced columns are read, compression is excellent on repeated
values, and vectorized execution processes batches.
⚠️ **`SELECT *` in a columnar warehouse is far more expensive relative to a targeted query
than it is in a row store.**

```
PARTITIONING       ⚠️ prune whole files — usually by date. The single biggest win
CLUSTERING/SORTING co-locate related rows; helps range and equality filters
PRE-AGGREGATION    ⚠️ materialize common roll-ups. Trades freshness and storage for latency
INCREMENTAL MODELS ⚠️ process only new data — and handle late arrivals (§6)
```
**⚠️ Order of attack when a dashboard is slow**: **check partition pruning is actually
happening** (⚠️ **read the query plan; a function applied to the partition column will
silently disable it**), **then reduce scanned columns, then pre-aggregate, then cache.**
**⚠️ Buying a bigger warehouse is the last resort and the most common first move.**

**Cost control**: ⚠️ **most warehouse spend comes from a small number of queries and from
dashboards auto-refreshing for nobody.** **Instrument query cost by dashboard, and
⚠️ audit scheduled refreshes against actual viewership — this is usually the single
largest available saving.**

---
