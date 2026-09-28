---
id: skill-architecture-style-decision-df0882945e
purpose: architecture style decision
source: src/vibey_tools/skills/plugins/software-architecture/skills/software-architecture/SKILL.md
requires: ["skill-core-philosophy-7bc657bf23"]
links: ["skill-api-style-selection-8790618ccd"]
---

## Architecture Style Decision

### Modular Monolith
- Single deployable, one pipeline, in-process calls
- Logical module boundaries enforced by tooling
- Schema-per-module, public APIs only, no cross-module internal imports
- Martin Fowler's "MonolithFirst" and Sam Newman's "never start with microservices" both apply: get boundaries right by living in the domain first

### Microservices
- Only when you have a concrete scaling, team, or regulatory driver you can name
- Supports: asynchronous (events/messages preferred for decoupling) and synchronous (REST, gRPC) comms
- Distributed transactions via **Saga pattern** with compensating transactions
- Supporting patterns: Sidecar, Ambassador, Anti-Corruption Layer (ACL)

### Migration: Strangler Fig + Anti-Corruption Layer
- Put legacy system behind a façade/proxy
- Start with the **easiest slice, not the most important one** — build confidence in the process
- Cut along **business boundaries, not technical ones**
- Build an ACL inside the monolith to translate calls to/from new services
- Watch failure modes: façade becoming its own monolith; "temporary" dual-write sync becoming permanent; migrations that never finish because they are horizontal instead of vertical slices

---
