---
id: skill-quirk-4-4-event-hook-hard-limits-and-no-ordering-guarantee-0cadf56166
purpose: quirk 4 4 event hook hard limits and no ordering guarantee
source: src/vibey_tools/skills/plugins/okta-workflows/skills/okta-workflows-hooks-streaming/SKILL.md
requires: ["skill-quirk-4-3-state-is-not-a-mutable-cross-page-accumulator-the-paginatedata-custom-parameter-limitation-5985dbdf1a"]
links: ["skill-quirk-4-5-api-endpoint-flows-drop-the-connection-at-60s-sync-120s-async-01f506191c"]
---

## Quirk 4.4 — Event hook hard limits and no ordering guarantee

Event hook completion timeout is 3 seconds with a single retry (4xx = no retry; 2xx = success;
redirects not followed). Limits: 400,000 applicable events / 24h per org (System Log warning at
280,000; resets 24h after the first event); max 25 active event hooks/org; max 500 flows using an Okta
event card as trigger; max 100 events per event hook payload; max 100 inline hooks/org (3s timeout
each). "There's no guarantee for the order of event hook delivery or flow execution" — a
deactivation-event flow may run before or after a reactivation, so the user state may have changed.

- *Source:* workflows-system-limits.htm
