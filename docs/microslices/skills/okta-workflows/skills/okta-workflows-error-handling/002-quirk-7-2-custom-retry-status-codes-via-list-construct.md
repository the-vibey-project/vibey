---
id: skill-quirk-7-2-custom-retry-status-codes-via-list-construct-19da3d36fb
purpose: quirk 7 2 custom retry status codes via list construct
source: src/vibey_tools/skills/plugins/okta-workflows/skills/okta-workflows-error-handling/SKILL.md
requires: ["skill-quirk-7-1-card-level-retry-only-fires-on-http-429-and-504-in-connector-builder-3e0d3ea23f"]
links: ["skill-quirk-7-3-max-3-nested-if-error-blocks-802f5121b0"]
---

## Quirk 7.2 — Custom retry status codes via List Construct

To retry on other codes, add a List Construct card listing the codes, rename its output (e.g.,
`retry_codes`), select "Specified errors" in the Raw Request card's Error Handling dialog, and drag
`retry_codes` into the Status Codes field.

- *Source:* best-practices-rate-limits.htm
