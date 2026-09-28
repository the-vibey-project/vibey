---
id: skill-quirk-7-4-error-propagation-from-helper-flows-441d85152c
purpose: quirk 7 4 error propagation from helper flows
source: src/vibey_tools/skills/plugins/okta-workflows/skills/okta-workflows-error-handling/SKILL.md
requires: ["skill-quirk-7-3-max-3-nested-if-error-blocks-802f5121b0"]
links: []
---

## Quirk 7.4 — Error propagation from helper flows

If Error/Try blocks act as anonymous helper flows; a Return inside them proceeds *after* the block
rather than halting. To propagate a hard failure to the parent, use Return Error / Return Error If
outside the block.

- *Source:* errorhandling_trycatch.htm
