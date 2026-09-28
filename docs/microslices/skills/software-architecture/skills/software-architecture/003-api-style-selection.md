---
id: skill-api-style-selection-8790618ccd
purpose: api style selection
source: src/vibey_tools/skills/plugins/software-architecture/skills/software-architecture/SKILL.md
requires: ["skill-architecture-style-decision-df0882945e"]
links: ["skill-python-backend-architecture-7c85633100"]
---

## API Style Selection

| Style | Best For | Avoid When |
|---|---|---|
| **tRPC** | TypeScript-first, full-stack, monorepos, internal tools | Public/polyglot APIs, multi-repo without versioning story |
| **GraphQL** | Complex client-driven data, multiple heterogeneous clients | Simple CRUD, performance-critical simple queries |
| **REST** | Public APIs, broad compatibility, HTTP caching, CRUD | High-throughput internal service calls |
| **gRPC** | Internal high-throughput service-to-service, streaming | Browser clients (needs transcoding proxy) |

**Hybrid is normal:** REST/GraphQL at the public boundary, tRPC or gRPC internally.

**tRPC specifics:** ~0.1ms request overhead in-process; reported 35–40% productivity gain vs REST for TypeScript projects (treat as directional). Contracts live in code — need explicit versioning story for public/multi-repo scenarios.

**GraphQL specifics:** N+1 problem solved with DataLoader batching. Mandatory query depth/complexity/cost limits to prevent DoS. One benchmark: GraphQL ~1864ms vs REST ~922ms for simple queries — GraphQL's win is flexibility, not raw speed.

---
