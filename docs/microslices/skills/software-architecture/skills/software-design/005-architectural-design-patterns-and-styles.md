---
id: skill-architectural-design-patterns-and-styles-02c80a309c
purpose: architectural design patterns and styles
source: src/vibey_tools/skills/plugins/software-architecture/skills/software-design/SKILL.md
requires: ["skill-principles-as-contextual-heuristics-5122902a99"]
links: ["skill-monolith-first-doctrine-64ccf8665a"]
---

## Architectural Design Patterns and Styles

### Layered / N-Tier
Common, but watch for:
- The "god layer" anti-pattern
- Greater than 50% pass-through layers with no logic → collapse the layer

### Hexagonal / Clean / Onion Architecture
All three are variations on one idea: a **dependency rule pointing inward to a framework-independent domain core**, with adapters at the edges for testability.
- **Hexagonal (Ports & Adapters):** Cockburn
- **Clean Architecture:** Martin
- **Onion Architecture:** Palermo

### Event-Driven Architecture
- Choreography vs. orchestration — each has distinct trade-offs
- Eventual consistency is the default consistency model
- Pattern vocabulary: Outbox, Saga, Idempotent Consumer, Claim Check

### CQRS and Event Sourcing
Powerful but frequently over-engineering for CRUD applications. Apply only when the complexity is justified by the requirements.

### Microservices
Bounded contexts as service boundaries; database-per-service. See Monolith-First Doctrine below before choosing this path.

### Strangler Fig, Sidecar/Service Mesh, Pipes and Filters, Space-Based and Cell-Based
For extreme scale or legacy migration. Cell-based architecture provides isolated failure domains.

---
