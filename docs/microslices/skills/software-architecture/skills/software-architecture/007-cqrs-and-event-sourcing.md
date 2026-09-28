---
id: skill-cqrs-and-event-sourcing-34cdbf3349
purpose: cqrs and event sourcing
source: src/vibey_tools/skills/plugins/software-architecture/skills/software-architecture/SKILL.md
requires: ["skill-azure-cloud-architecture-6770e0d67a"]
links: ["skill-observability-54fe73659e"]
---

## CQRS and Event Sourcing

**Use incrementally and surgically — not as a default.**

When CQRS/event sourcing hurts:
- Query-heavy with many low-latency read shapes — forces projections, adds operational burden
- Team can't commit to event-schema governance — brittle replays and broken consumers
- Adopted too early, before understanding the domain — painful refactoring later ("day-two problem")

**Recommended sequence:**
1. Strengthen the domain model in current persistence first
2. Introduce CQRS only for read models that actually hurt
3. Add an outbox if you publish messages from the write DB
4. Adopt event sourcing for one aggregate where history is genuinely the product (finance, entitlements, audit-heavy workflows)

**Apply Postel's Law:** conservative in what you emit, liberal in what you accept (event schema evolution).

---
