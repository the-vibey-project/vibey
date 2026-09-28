---
id: skill-quirk-3-5-no-native-upsert-concurrent-write-race-risk-theory-722d313726
purpose: quirk 3 5 no native upsert concurrent write race risk theory
source: src/vibey_tools/skills/plugins/okta-workflows/skills/okta-workflows-tables/SKILL.md
requires: ["skill-quirk-3-4-where-expression-json-quirk-when-testing-with-variables-35aa4c1134"]
links: ["skill-quirk-3-6-high-frequency-table-requests-trigger-throttling-9df8d29629"]
---

## Quirk 3.5 — No native upsert / concurrent-write race risk (THEORY)

There is no atomic upsert; the documented pattern is Search Rows → If/Else on Row ID empty → Create
Row or Update Row. When multiple concurrent flow executions (e.g., many event-hook-triggered flows)
run this read-then-write against the same table/key, there is a classic race window that can create
duplicate rows. **This concurrency/locking risk is a plausible-but-not-explicitly-documented inference
from the read-then-write pattern — label as THEORY.** Mitigation: funnel all table writes through a
single-concurrency (`concurrency=1`) helper flow or a scheduled batch to serialize writes.

- *Sources:* support.okta.com how-to-conditionally-update-a-table; upsert-example
