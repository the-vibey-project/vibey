---
id: skill-quirk-6-3-automated-flow-throttling-is-now-a-platform-feature-a9ca6c9d30
purpose: quirk 6 3 automated flow throttling is now a platform feature
source: src/vibey_tools/skills/plugins/okta-workflows/skills/okta-workflows-execution-limits/SKILL.md
requires: ["skill-quirk-6-2-active-flow-count-is-plan-gated-6e40363e1e"]
links: ["skill-quirk-6-4-export-flow-rate-limits-15-min-window-a50f89c982"]
---

## Quirk 6.3 — Automated flow throttling is now a platform feature

The internal system-limit analyzer throttles flows exceeding CPU time, table requests, memory, or
helper-flow counts within a window: "Okta has identified that this flow has exceeded expected resource
usage. This flow will complete, but the resource allocation for it has been limited." Loop-heavy and
table-heavy sync flows are prime candidates; Free Trial and Starter plans have a lower throttling
threshold. Throttling "doesn't impact or prevent the completion of a flow."

- *Source:* about-execution-limits.htm
