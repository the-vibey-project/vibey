---
id: skill-sequencing-decisions-cfd98ecb39
purpose: sequencing decisions
source: src/vibey_tools/skills/plugins/software-architecture/skills/software-architecture/SKILL.md
requires: ["skill-process-and-people-74f890c97f"]
links: ["skill-staged-rollout-thresholds-96f6d9d637"]
---

## Sequencing Decisions

### New Large Project
1. Domain & teams first (event storming, context map, inverse Conway)
2. Repository & build topology (uv workspace monorepo for Python; Turborepo for frontend)
3. Architecture style: **modular monolith** with enforced module boundaries
4. API contracts (tRPC internally; REST/GraphQL at public boundaries; gRPC for high-throughput internal)
5. Backend skeleton: FastAPI app factory + lifespan; layered architecture; repository + UoW; DI; Alembic with expand-contract from day one
6. Frontend skeleton: App Router + FSD; Server Components default; TanStack Query + Zustand/Jotai + React Hook Form + Zod; Auth
7. Azure foundation: enterprise-scale landing zone; hub-and-spoke; Bicep with AVM; managed identities + Key Vault + Private Endpoints; Log Analytics/Defender/Sentinel
8. Cross-cutting from the start: OpenTelemetry → Azure Monitor; structlog; GitHub Actions with env promotion + feature flags; ADRs in-repo

### Evolving an Existing System
1. **Instrument and observe first** — wire OpenTelemetry; find the painful read models, hot paths, deploy-coupling bottlenecks
2. **Introduce module boundaries inside the monolith** before any extraction; add architecture tests
3. **Strangler fig the first slice** — easiest business-bounded slice; façade; ACL; route a percentage; compare behavior before cutover
4. **Extract a service only on a concrete signal** (independent scaling, team friction, fault isolation)
5. **Adopt CQRS/event sourcing surgically** — only where it pays rent
6. **Migrate data with expand-contract** — always backward-compatible

---
