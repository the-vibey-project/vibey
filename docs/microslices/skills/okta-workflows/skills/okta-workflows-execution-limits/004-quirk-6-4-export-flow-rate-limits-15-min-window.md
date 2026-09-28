---
id: skill-quirk-6-4-export-flow-rate-limits-15-min-window-a50f89c982
purpose: quirk 6 4 export flow rate limits 15 min window
source: src/vibey_tools/skills/plugins/okta-workflows/skills/okta-workflows-execution-limits/SKILL.md
requires: ["skill-quirk-6-3-automated-flow-throttling-is-now-a-platform-feature-a9ca6c9d30"]
links: []
---

## Quirk 6.4 — Export flow rate limits (15-min window)

Export capacity resets every 15 minutes; caps are plan-based (Starter 10, Light 100, Medium 300,
Maximum 1000). Exceeding the cap fails the entire export with no partial output.

- *Source:* workflows-system-limits.htm
