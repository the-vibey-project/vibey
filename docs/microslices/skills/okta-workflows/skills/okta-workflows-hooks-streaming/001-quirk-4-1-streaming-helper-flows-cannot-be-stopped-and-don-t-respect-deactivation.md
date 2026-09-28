---
id: skill-quirk-4-1-streaming-helper-flows-cannot-be-stopped-and-don-t-respect-deactivation-f508bad04d
purpose: quirk 4 1 streaming helper flows cannot be stopped and don t respect deactivation
source: src/vibey_tools/skills/plugins/okta-workflows/skills/okta-workflows-hooks-streaming/SKILL.md
requires: []
links: ["skill-quirk-4-2-streaming-helper-flow-contract-is-rigid-inputs-must-be-named-record-and-state-both-object-6d3f511981"]
---

## Quirk 4.1 — Streaming helper flows cannot be stopped and don't respect deactivation

"You can't stop a flow once the execution begins. A helper flow that streams data from a search or
list card runs until the API returns all records or the flow reaches the specified maximum number of
records. Also, an in-progress flow doesn't stop running if you deactivate the flow." Streaming handles
data sets that exceed the 10,000-record standard search limit, up to a **1 million-record maximum**;
"Processing 500,000 records takes approximately 13 hours. Processing 1 million records takes
approximately 25 hours."

- *Source:* about-streaming.htm
