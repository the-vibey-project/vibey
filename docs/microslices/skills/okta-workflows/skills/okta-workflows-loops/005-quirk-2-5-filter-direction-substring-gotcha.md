---
id: skill-quirk-2-5-filter-direction-substring-gotcha-7b43767c21
purpose: quirk 2 5 filter direction substring gotcha
source: src/vibey_tools/skills/plugins/okta-workflows/skills/okta-workflows-loops/SKILL.md
requires: ["skill-quirk-2-4-deeply-nested-iteration-cards-can-trigger-cpu-time-throttling-68e7853084"]
links: []
---

## Quirk 2.5 — Filter direction / substring gotcha

The built-in List - Filter checks substring membership in a specific direction; community guidance
(Max Katz) recommends the List - Filter (Custom) card with a helper flow for "starts with"/arbitrary
text matching, since the built-in filter and Tables searches don't support starts-with text
semantics.

- *Source:* maxkatz.net custom list filter guide
