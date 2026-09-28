---
id: skill-quirk-1-6-if-else-supports-only-one-condition-07915c6db7
purpose: quirk 1 6 if else supports only one condition
source: src/vibey_tools/skills/plugins/okta-workflows/skills/okta-workflows-branching/SKILL.md
requires: ["skill-quirk-1-5-cannot-drag-outputs-from-inside-a-branch-to-cards-after-the-block-e2d6298459"]
links: []
---

## Quirk 1.6 — If/Else supports only ONE condition

The Branching - If/Else card doesn't support multiple conditions. Use True/False Compare cards
feeding an And/Or/Not/XNOR card, then pass the single boolean into If/Else; or use If/ElseIf.

- *Source:* maxkatz.net 2023/07/25
