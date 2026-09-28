---
id: skill-principles-as-contextual-heuristics-5122902a99
purpose: principles as contextual heuristics
source: src/vibey_tools/skills/plugins/software-architecture/skills/software-design/SKILL.md
requires: ["skill-design-process-by-scale-c476d426c3"]
links: ["skill-architectural-design-patterns-and-styles-02c80a309c"]
---

## Principles as Contextual Heuristics

### SOLID
**SRP, OCP, LSP, ISP, DIP** — remains the default OO vocabulary but should be treated as heuristics, not binary laws.

**Dan North's CUPID critique (2021):** "Every single element of SOLID is wrong." His alternative: **CUPID** — Composable, Unix-philosophy, Predictable, Idiomatic, Domain-based. North reframes these as *properties* (a direction to move toward) rather than *principles* (binary rules).

> "Principles are like rules: you are either compliant or you are not... Instead, I started thinking about properties: qualities or characteristics of code... Properties define a goal or centre to move towards." — Dan North

**2025 practical view:** SOLID works well in large monolithic backends but is a poor fit for data engineering and functional styles.

### DRY — and the Wrong Abstraction
DRY is about **knowledge duplication, not code duplication**. Two identical code fragments expressing different domain concepts do NOT violate DRY.

**Sandi Metz's critical nuance:** "Duplication is far cheaper than the wrong abstraction." When an abstraction has gone wrong:

> "Re-introduce duplication by inlining the abstracted code back into every caller... When the abstraction is wrong, the fastest way forward is back." — Sandi Metz

**Fowler's Rule of Three:** Wait for three instances before abstracting. This is the practical guard against premature abstraction.

### KISS, YAGNI, and Other Foundational Principles
- **KISS:** Hardest to follow — experienced engineers over-engineer
- **YAGNI:** Defer speculative work; don't build for requirements you don't have
- **Separation of Concerns:** The most fundamental design principle
- **High cohesion / low coupling:** Measurable via Ford & Richards's connascence, instability, abstractness, and distance-from-main-sequence metrics
- **Law of Demeter:** Talk only to your immediate collaborators
- **Composition over inheritance:** Prefer delegation and composition
- **Fail-fast:** Surface errors as early as possible
- **Encapsulation as information hiding (Parnas):** Hide decisions likely to change — Sam Newman invokes this for database decomposition in microservices

---
