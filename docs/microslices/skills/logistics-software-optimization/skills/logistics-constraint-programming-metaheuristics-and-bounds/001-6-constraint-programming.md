---
id: skill-6-constraint-programming-b804171bbf
purpose: 6 constraint programming
source: src/vibey_tools/skills/plugins/logistics-software-optimization/skills/logistics-constraint-programming-metaheuristics-and-bounds/SKILL.md
requires: []
links: ["skill-7-metaheuristics-e8b810036e"]
---

## §6. Constraint Programming

**⚠️ A different paradigm, and often better than MIP for scheduling and sequencing.**
**CP works by constraint propagation — domain filtering — plus search, rather than by LP
relaxation.**
**⚠️ Where CP wins**: **scheduling with precedence and resource constraints, rostering,
problems with complex logical conditions, and anything with rich global constraints
(`alldifferent`, `cumulative`, `noOverlap`, `element`).** ⚠️ **CP-SAT in particular
(OR-Tools) is exceptionally strong on scheduling and has largely displaced hand-rolled
approaches for those problems.**
**⚠️ Where MIP wins**: **problems with strong linear structure, cost-driven objectives, and
where you need good bounds.**
⚠️ **Modern CP-SAT solvers hybridize — they include SAT-style clause learning and
LP relaxations — so the paradigm boundary is blurrier than it was.**

---
