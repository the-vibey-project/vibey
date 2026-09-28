---
id: skill-15-scheduling-4d6c60f463
purpose: 15 scheduling
source: src/vibey_tools/skills/plugins/logistics-software-optimization/skills/logistics-routing-packing-scheduling-and-network-design/SKILL.md
requires: ["skill-14-assignment-and-matching-065baa1dc2"]
links: ["skill-16-facility-location-and-network-design-43d135b9f3"]
---

## §15. Scheduling

**Job shop, flow shop, parallel machines, RCPSP, crew scheduling and rostering.**
⚠️ **Crew scheduling and rostering are the classic column-generation domain (§4 → `logistics-why-projects-fail-complexity-and-modeling`) — the
"columns" are legal duty pairings, of which there are astronomically many.**
**⚠️ CP-SAT is usually the right first tool for shop scheduling** (§6 → `logistics-constraint-programming-metaheuristics-and-bounds`).
**⚠️ Note the recurring structure**: **most scheduling problems are "assign + sequence +
time," and the tractable decomposition is often to fix the assignment, solve the sequence,
then repair.**

---
