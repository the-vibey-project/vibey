---
id: skill-quirk-2-4-deeply-nested-iteration-cards-can-trigger-cpu-time-throttling-68e7853084
purpose: quirk 2 4 deeply nested iteration cards can trigger cpu time throttling
source: src/vibey_tools/skills/plugins/okta-workflows/skills/okta-workflows-loops/SKILL.md
requires: ["skill-quirk-2-3-plain-for-each-returns-no-outputs-aba3a12725"]
links: ["skill-quirk-2-5-filter-direction-substring-gotcha-7b43767c21"]
---

## Quirk 2.4 — Deeply nested iteration cards can trigger CPU-time throttling

Per the Execution limits page: "Flows that exceed CPU time limits may use highly nested child flow
structures with nested iteration cards, such as For Each, Map, or Reduce. Deeply nested iteration
cards can exponentially grow the number of executions."

- *Source:* about-execution-limits.htm
