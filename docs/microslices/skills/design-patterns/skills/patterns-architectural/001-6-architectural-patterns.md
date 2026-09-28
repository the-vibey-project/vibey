---
id: skill-6-architectural-patterns-35cd40d019
purpose: 6 architectural patterns
source: src/vibey_tools/skills/plugins/design-patterns/skills/patterns-architectural/SKILL.md
requires: []
links: ["skill-7-monoliths-modules-and-microservices-791440a67f"]
---

## §6. Architectural Patterns

### 6.1 Layered

Presentation → Application → Domain → Infrastructure. **Familiar, easy to explain, and
adequate for a great deal of software.** ⚠️ Its failure modes: **anemic domain models**
(logic drains into the service layer, leaving data-bags — see §14 → `patterns-reference`), layer-skipping that
nobody notices, and **dependency flowing the wrong way toward infrastructure.**

### 6.2 Hexagonal / Ports and Adapters (and Clean, and Onion)

**[DURABLE] The single most valuable architectural idea for most business applications,
and the family is largely one idea under three names.**

**Domain logic in the centre, knowing nothing about the outside world. Ports are
interfaces the domain defines. Adapters implement them for a database, an HTTP API, a
queue, a third-party service.** ⚠️ **The dependency rule is the whole point: dependencies
point inward, always.** Infrastructure depends on the domain; the domain depends on
nothing.

**What you actually get**: the domain is testable without a database or a network; you can
replace infrastructure without touching business rules; and **the business logic is
findable**, which matters more than it sounds.

**⚠️ What it costs**: more indirection, more files, and **it's genuinely overkill for a
CRUD app.** The honest heuristic: **if your domain logic is thin, you don't need this** —
and much software has thin domain logic.

### 6.3 Domain-Driven Design

**Strategic DDD is the more valuable half and the more neglected one**: **bounded
contexts** (⚠️ **the single most useful concept here** — the same word means different
things in different parts of the business, and pretending otherwise produces the
universal-model disaster), **ubiquitous language**, and **context mapping**.

**Tactical DDD**: entities, value objects (**⚠️ underused — most "primitives" in a domain
are value objects with invariants**), aggregates (**consistency boundaries — and the "one
aggregate per transaction" rule is what makes them useful**), repositories, domain events,
domain services.

**⚠️ The characteristic DDD failure is adopting the tactical patterns without the strategic
work** — you get repositories and value objects laid over a model nobody talked to the
business about, which is the ceremony without the benefit.

---
