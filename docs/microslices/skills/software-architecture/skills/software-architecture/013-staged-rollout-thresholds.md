---
id: skill-staged-rollout-thresholds-96f6d9d637
purpose: staged rollout thresholds
source: src/vibey_tools/skills/plugins/software-architecture/skills/software-architecture/SKILL.md
requires: ["skill-sequencing-decisions-cfd98ecb39"]
links: ["skill-common-mistakes-to-avoid-25a04a1937"]
---

## Staged Rollout Thresholds

| Stage | Description | Advance When |
|---|---|---|
| Stage 0 (weeks 1–4) | Enterprise-scale landing zone; monorepos; CI/CD; OpenTelemetry; ADRs | Request traces end-to-end in Application Insights |
| Stage 1 (months 1–6) | FastAPI + Next.js modular monolith with enforced boundaries; expand-contract Alembic | Module boundaries hold in CI; high deploy frequency, clean rollbacks |
| Stage 2 | Extract services on concrete signals only; strangler fig + ACL; Linkerd only if ≥ a handful of services needing mTLS | Can name the concrete scaling/coupling/regulatory driver |
| Stage 3 | Multi-region active-active (Front Door + Cosmos DB multi-region writes + multi-region APIM) | Business SLA/geographic requirement justifies ~3–6x cost |

**Benchmark triggers:**
- Team crossing ~10 engineers → consider modules
- Team crossing ~30–40 engineers → consider first extraction
- Team crossing ~100 engineers → microservices likely justified
- One module needing ~10x the scale of others → extract it
- CI exceeding ~10–20 min → adopt Turborepo remote cache
- Query latency / read-shape pain → introduce CQRS read models
- Audit/history becoming a business requirement → event-source that one aggregate

---
