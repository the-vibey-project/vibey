---
id: skill-8-caching-and-freshness-cc07085fc7
purpose: 8 caching and freshness
source: src/vibey_tools/skills/plugins/reporting-and-dashboards/skills/reporting-semantic-layer-time-and-performance/SKILL.md
requires: ["skill-7-query-performance-ddc69f6aec"]
links: []
---

## §8. Caching and Freshness

```
Result cache       identical query → stored result. ⚠️ Free, and invalidation is the
                   whole problem
Pre-aggregation    materialized roll-ups (§7)
Extract/import     ⚠️ BI tool holds its own copy (Power BI import, Tableau extract).
                   Fast, and now you have two sources of truth to keep in sync
Live/DirectQuery   always current, always slower, ⚠️ and every viewer hits the warehouse
```
**⚠️ Freshness is a product requirement, not a technical default.** **Ask what decision the
data supports and how stale it can be** — ⚠️ **"real-time" is asked for far more often than
it is needed, and it costs an order of magnitude more.** **A daily-refreshed dashboard
that everyone trusts beats a real-time one that's frequently broken.**
**⚠️ Always show the last-refreshed timestamp.** **A stale dashboard that looks live is
worse than no dashboard.**
