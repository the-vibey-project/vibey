---
id: skill-refactoring-and-evolution-63da9eabd9
purpose: refactoring and evolution
source: src/vibey_tools/skills/plugins/software-architecture/skills/software-design/SKILL.md
requires: ["skill-quality-metrics-and-anti-patterns-f2e46a0ea3"]
links: ["skill-benchmarks-that-should-change-your-approach-4b199a0b89"]
---

## Refactoring and Evolution

### Beck's *Tidy First?* (2023) — 15 Tidyings
Structural changes go in **separate commits from behavioral changes**. Representative tidyings:
- Guard clauses (replace nested conditionals with early returns)
- Extract helper (isolate a coherent chunk of logic)
- Normalize symmetries (make similar things look similar)

### Debt Paydown Strategies
- **Opportunistic Boy Scout Rule:** Leave code better than you found it — judiciously, within scope
- **Scheduled debt sprints:** Periodic dedicated refactoring iterations
- **Targeted architectural redesign:** For pervasive structural problems

### Fitness Function Evolution
As the architecture changes, the fitness functions must change with it. Evolving fitness functions are how you avoid governance debt.

---
