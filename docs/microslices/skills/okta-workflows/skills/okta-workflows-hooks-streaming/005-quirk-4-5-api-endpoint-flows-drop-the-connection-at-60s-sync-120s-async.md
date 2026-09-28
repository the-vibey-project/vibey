---
id: skill-quirk-4-5-api-endpoint-flows-drop-the-connection-at-60s-sync-120s-async-01f506191c
purpose: quirk 4 5 api endpoint flows drop the connection at 60s sync 120s async
source: src/vibey_tools/skills/plugins/okta-workflows/skills/okta-workflows-hooks-streaming/SKILL.md
requires: ["skill-quirk-4-4-event-hook-hard-limits-and-no-ordering-guarantee-0cadf56166"]
links: ["skill-quirk-4-6-finding-the-calling-flow-from-a-helper-a9d596478c"]
---

## Quirk 4.5 — API Endpoint flows drop the connection at 60s (sync) / 120s (async)

Synchronous API-endpoint connections terminate at 60 seconds (the flow itself keeps running); async
waits drop at 120s. Inline hooks time out at 3s. Workaround: add API Connector Close as the first card
to release the HTTP connection immediately, then process asynchronously; or use Call Flow Async +
Return Raw.

- *Sources:* workflows-system-limits.htm; architecture-best-practices.htm
