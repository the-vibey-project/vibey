---
id: skill-quirk-3-6-high-frequency-table-requests-trigger-throttling-9df8d29629
purpose: quirk 3 6 high frequency table requests trigger throttling
source: src/vibey_tools/skills/plugins/okta-workflows/skills/okta-workflows-tables/SKILL.md
requires: ["skill-quirk-3-5-no-native-upsert-concurrent-write-race-risk-theory-722d313726"]
links: []
---

## Quirk 3.6 — High-frequency table requests trigger throttling

"Table requests" is an explicit throttling resource: "Flows with highly active event cards that make
requests through Tables function cards" are called out as throttling-eligible.

- *Source:* about-execution-limits.htm
