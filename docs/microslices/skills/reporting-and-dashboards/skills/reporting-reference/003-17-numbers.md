---
id: skill-17-numbers-36a88d0931
purpose: 17 numbers
source: src/vibey_tools/skills/plugins/reporting-and-dashboards/skills/reporting-reference/SKILL.md
requires: ["skill-16-what-moved-verified-august-2026-b3232ed4e3"]
links: ["skill-18-books-438c4b4ea3"]
---

## §17. Numbers

```
BENCHMARKS (text-to-SQL) ⚠️
Spider 1.0 ~91% · BIRD ~73% · ⚠️ Spider 2.0 (enterprise) ~21%
Human expert on BIRD ~92–93%
⚠️ Cross-benchmark figures are NOT directly comparable

PERCEPTION (Cleveland-McGill) ⚠️
position > length > angle > area > colour saturation
~8% of men have some colour vision deficiency

DASHBOARD
5–9 elements max · ⚠️ above-the-fold is what gets seen
Always show last-refreshed time

MODELLING
⚠️ Declare the grain first
SCD Type 1 = overwrite (history lost) · Type 2 = new row + validity dates
Fully / semi- / non-additive — ⚠️ know which every measure is

TIME
Store UTC · ⚠️ ISO week 1 contains the first Thursday
4-4-5 retail calendars · ⚠️ DST days are 23 or 25 hours

PERFORMANCE
⚠️ Partition pruning is the biggest single win — verify in the query plan
Columnar: SELECT * is disproportionately expensive
```

---
