---
id: skill-quirk-4-2-streaming-helper-flow-contract-is-rigid-inputs-must-be-named-record-and-state-both-object-6d3f511981
purpose: quirk 4 2 streaming helper flow contract is rigid inputs must be named record and state both object
source: src/vibey_tools/skills/plugins/okta-workflows/skills/okta-workflows-hooks-streaming/SKILL.md
requires: ["skill-quirk-4-1-streaming-helper-flows-cannot-be-stopped-and-don-t-respect-deactivation-f508bad04d"]
links: ["skill-quirk-4-3-state-is-not-a-mutable-cross-page-accumulator-the-paginatedata-custom-parameter-limitation-5985dbdf1a"]
---

## Quirk 4.2 — Streaming helper flow contract is rigid: inputs MUST be named `Record` and `State` (both Object)

"In the helper flow, create two input entries: Record and State. Set the type for both fields to
Object… The helper flow requires the input fields to be named Record and State." `Record` = current
item being processed; `State` = parent-defined extra inputs sent with every record.

- *Source:* search-with-streaming.htm
