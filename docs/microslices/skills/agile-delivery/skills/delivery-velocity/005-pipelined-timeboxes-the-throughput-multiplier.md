---
id: skill-pipelined-timeboxes-the-throughput-multiplier-d170db2450
purpose: pipelined timeboxes the throughput multiplier
source: src/vibey_tools/skills/plugins/agile-delivery/skills/delivery-velocity/SKILL.md
requires: ["skill-little-s-law-and-wip-limits-4810acb33c"]
links: ["skill-team-size-5-2-people-864bca810e"]
---

## Pipelined Timeboxes: The Throughput Multiplier

Jalote et al.'s formalization: an **n-stage pipelined timebox delivers n times the throughput** of serial iterations at steady state.

**Example — 3-stage pipeline with 3-week cycles:**
- Stage 1: Requirements + design (weeks 1–3)
- Stage 2: Development (weeks 4–6)
- Stage 3: Testing + deployment (weeks 7–9)

In serial mode: one release every 9 weeks.
In pipelined mode: first release at week 9, then **one release every 3 weeks** thereafter — 3× the throughput.

**Implementation:** Structure work so multiple initiatives can be in different pipeline stages simultaneously. While one initiative is in development, the next is in design, and the prior one is being validated.

---
