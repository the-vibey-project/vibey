---
id: skill-event-driven-vs-request-response-628cab3d73
purpose: event driven vs request response
source: src/vibey_tools/skills/plugins/software-architecture/skills/architecture-patterns/SKILL.md
requires: ["skill-platform-engineering-0f4864a139"]
links: ["skill-make-vs-buy-vs-configure-083116781f"]
---

## Event-Driven vs Request-Response
- Synchronous: when the user needs an immediate consistent answer
- Asynchronous: for background work, decoupling, resilience
- The **dual-write problem** demands either **Outbox** or **Saga** — never two independent writes
