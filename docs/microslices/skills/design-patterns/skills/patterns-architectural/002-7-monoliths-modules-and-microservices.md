---
id: skill-7-monoliths-modules-and-microservices-791440a67f
purpose: 7 monoliths modules and microservices
source: src/vibey_tools/skills/plugins/design-patterns/skills/patterns-architectural/SKILL.md
requires: ["skill-6-architectural-patterns-35cd40d019"]
links: []
---

## §7. Monoliths, Modules, and Microservices

**[CONTESTED, though the pendulum has swung noticeably.]**

**[DURABLE] The modular monolith is the correct default for most teams**: one deployable,
strong internal module boundaries, no network between your own components. You get
enforced boundaries without distributed-systems tax.

**⚠️ Microservices buy independent deployment and scaling, and they cost you: distributed
transactions (§8 → `patterns-distributed-concurrency-and-messaging`), network failure as a permanent condition, debugging across process
boundaries, eventual consistency everywhere, and operational overhead per service.**
The honest framing: **microservices are an organizational solution to a team-coordination
problem, adopted for a technical-sounding reason.** If your teams aren't blocked on each
other's deploys, you're paying the cost without collecting the benefit.

**Related patterns**: **Strangler Fig** (§13 → `patterns-llm-agentic-and-legacy-migration`), **API Gateway**, **Backend for Frontend
(BFF)**, **Sidecar / Ambassador** (cross-cutting concerns beside rather than inside your
process — the basis of service meshes), **Anti-Corruption Layer** (⚠️ **the essential
pattern when integrating a legacy or third-party model you don't control** — translate at
the boundary so their model doesn't leak into yours).

**Serverless/event-driven adds its own**: function-per-endpoint, fan-out/fan-in, and
⚠️ **cold-start and statelessness constraints that are design forces, not implementation
details.**
