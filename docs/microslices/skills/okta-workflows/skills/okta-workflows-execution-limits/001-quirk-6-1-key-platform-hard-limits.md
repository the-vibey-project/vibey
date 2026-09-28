---
id: skill-quirk-6-1-key-platform-hard-limits-34fc3f7e73
purpose: quirk 6 1 key platform hard limits
source: src/vibey_tools/skills/plugins/okta-workflows/skills/okta-workflows-execution-limits/SKILL.md
requires: []
links: ["skill-quirk-6-2-active-flow-count-is-plan-gated-6e40363e1e"]
---

## Quirk 6.1 — Key platform hard limits

Instance memory 100 MB; max steps/flow 2 million; recursion limit 250 (error: "Stack limit
exceeded"); payload limit 1 MB per execution-history message (message: "The data returned
successfully, but is too large to display" — explicitly NOT an error, no data impact); flow-execution
rate limit 10 invocations/sec/flow (then 429); execution history retained 30 days; file attachments 10
MB, download/upload 2 GB, SFTP 25 MB, file retention 30 days; max pause duration 30 days.

- *Source:* workflows-system-limits.htm
