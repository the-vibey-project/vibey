---
id: skill-quirk-3-4-where-expression-json-quirk-when-testing-with-variables-35aa4c1134
purpose: quirk 3 4 where expression json quirk when testing with variables
source: src/vibey_tools/skills/plugins/okta-workflows/skills/okta-workflows-tables/SKILL.md
requires: ["skill-quirk-3-3-table-hard-limits-8a775175e3"]
links: ["skill-quirk-3-5-no-native-upsert-concurrent-write-race-risk-theory-722d313726"]
---

## Quirk 3.4 — Where Expression JSON quirk when testing with variables

When passing a variable into the Where Expression and testing the card, you must hand-edit the Where
Expression JSON (lhs/op/join/rhs structure) or the test returns wrong output. Example:
`{"expr":[{"lhs":"Country","op":"=","join":"AND","rhs":"Brazil"},{"lhs":"Code","op":"=","join":"AND","rhs":"BR"}]}`.

- *Source:* maxkatz.net 2023/10/25
