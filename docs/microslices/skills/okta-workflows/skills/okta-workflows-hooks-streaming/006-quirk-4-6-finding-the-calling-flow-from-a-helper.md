---
id: skill-quirk-4-6-finding-the-calling-flow-from-a-helper-a9d596478c
purpose: quirk 4 6 finding the calling flow from a helper
source: src/vibey_tools/skills/plugins/okta-workflows/skills/okta-workflows-hooks-streaming/SKILL.md
requires: ["skill-quirk-4-5-api-endpoint-flows-drop-the-connection-at-60s-sync-120s-async-01f506191c"]
links: []
---

## Quirk 4.6 — Finding the calling flow from a helper

The first Helper Flow card exposes a `Caller` object containing `root_wf_id`. `root_wf_id` reliably
resolves only the immediate caller one level deep; for robust multi-level lineage use Event metadata
in Execution Log Streaming.

- *Source:* maxkatz.net Tips #57
