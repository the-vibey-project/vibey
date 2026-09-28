---
id: skill-domain-driven-design-ddd-ea51814190
purpose: domain driven design ddd
source: src/vibey_tools/skills/plugins/software-architecture/skills/software-design/SKILL.md
requires: ["skill-monolith-first-doctrine-64ccf8665a"]
links: ["skill-architecture-decision-records-adrs-049a181753"]
---

## Domain-Driven Design (DDD)

### Strategic DDD
**Bounded Contexts:** The primary tool for managing complexity at scale. Each context has its own ubiquitous language and model.

**Language test:** When the same word means different things in two parts of the system, you've found a context boundary.

**Context Maps** (integration patterns between contexts):
- Shared Kernel — shared model owned jointly
- Customer-Supplier — upstream/downstream relationship
- Conformist — downstream conforms to upstream's model
- Anticorruption Layer (ACL) — translation layer protecting a new context from a legacy/foreign model
- Open-Host Service — well-defined API for others to integrate against

**Subdomain classification:**
- **Core domain:** Competitive advantage; invest heavily here
- **Supporting subdomain:** Needed but not differentiating; custom-build if required
- **Generic subdomain:** Buy or use open-source

**Accessible framing (Khononov):** Use "Functional Area" instead of "Bounded Context" and "Shared Vocabulary" instead of "Ubiquitous Language" to avoid alienating stakeholders.

### Tactical DDD
- **Entities:** Have identity that persists across state changes
- **Value Objects:** Defined entirely by their attributes; immutable
- **Aggregates:** Consistency boundary; keep small; reference other aggregates by ID only
- **Domain Events:** Record that something meaningful happened in the domain
- **Repositories:** Abstraction over persistence for aggregates
- **Domain Services:** Stateless operations that don't belong to a single entity
- **Application Services:** Orchestrate use cases, coordinate infrastructure

**DDD-lite:** Tactical patterns without full ceremony — recommended for most teams. Full DDD is overkill for simple CRUD.

### Event Storming (Brandolini)
The dominant 2024–2026 collaborative technique for discovering bounded contexts and aggregates.

**Core insight:** "Merge the people, split the software."

Process: Domain experts and developers use sticky notes on a large surface to map domain events, commands, aggregates, and policies. Outputs let teams "confidently design the data models and determine the appropriate software architecture."

**Domain Storytelling:** Uni-directional flows indicate bounded context candidates.

---
