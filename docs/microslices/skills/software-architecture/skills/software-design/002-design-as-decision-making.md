---
id: skill-design-as-decision-making-96593e366c
purpose: design as decision making
source: src/vibey_tools/skills/plugins/software-architecture/skills/software-design/SKILL.md
requires: ["skill-core-philosophy-4dcd0a67f5"]
links: ["skill-design-process-by-scale-c476d426c3"]
---

## Design as Decision-Making

### What Architecture Actually Is
Ford & Richards define architecture as: **structure + architecture characteristics ("-ilities") + architecture decisions + design principles.**

Useful working distinction:
- **Architecture** = decisions that are expensive to reverse ("the stuff that's hard to change later")
- **High-level/detailed design** = component and class decisions that are cheaper to change

The boundary is fluid — microservices made "change a first-class design consideration," partly invalidating the old "hard to change" definition.

### JEDUF — Just-Enough Design Up Front
The empirical evidence for the "cost-of-change curve" (Boehm's 1970s hypothesis that defects cost exponentially more to fix later) is **weakly supported**. A 2016 Menzies et al. study found "no credence to the hypothesis" across 171 projects. The honest position:

> **JEDUF:** Design enough to de-risk irreversible decisions; defer the rest. Most real design happens iteratively during implementation.

### Type 1 / Type 2 Decision Mapping (Bezos)
- **Invest up-front effort in irreversible (Type 1) decisions:** data model, service boundaries, public API contracts, persistence choices
- **Defer reversible (Type 2) decisions:** internal class structure, library choices behind an interface

Kent Beck's *Tidy First?* (2023) formalizes the economic logic: structural changes are reversible options ("just as a bad haircut is more reversible than a bad tattoo"). Software value = discounted future cash flows + the value of options created by good structure. Sometimes ship behavior first and tidy after — the time value of money applies.

### The Canonical Decision Framework
1. Identify options
2. Analyze trade-offs
3. Decide
4. Record (in an ADR)

**Three recurring decisions at every scale:** build/buy/reuse, sync/async, stateful/stateless.

Watch for **Brooks's Second System Effect** (over-engineering the rewrite) and apply YAGNI to defer speculative generality.

### Essential vs. Accidental Complexity
- **Essential complexity:** inherent to the domain — cannot be eliminated
- **Accidental complexity:** introduced by the solution — always worth reducing
- **Core domain:** your competitive advantage; worth heavy design investment
- **Generic/supporting subdomains:** candidates for buy-or-off-the-shelf (DDD strategic distinction)

---
