---
id: skill-catalog-azure-architecture-center-791795e9f3
purpose: catalog azure architecture center
source: src/vibey_tools/skills/plugins/software-architecture/skills/architecture-patterns/SKILL.md
requires: ["skill-load-balancing-decision-matrix-75537f2ba4"]
links: ["skill-high-availability-b781d238b7"]
---

## Catalog (Azure Architecture Center)

| Pattern | Purpose | Azure Implementation |
|---|---|---|
| **Retry with exponential backoff + jitter** | Handle transient failures | Polly (.NET), Tenacity (Python) |
| **Circuit Breaker** (Closed/Open/Half-Open) | Stop calling a failing dependency | Polly; APIM backend circuit breaker |
| **Bulkhead** | Isolate resource pools | Thread pool isolation; ACA scale units |
| **Timeout** | Fail fast | Set at every network hop |
| **Fallback** | Graceful degradation | Return cached data, default response |
| **Health Endpoint Monitoring** | `/health/live`, `/health/ready` | App Service health check; AKS probes |
| **Idempotency** | Safe retry of mutations | Idempotency keys on write endpoints |
| **Saga** | Distributed transactions | Choreography vs orchestration; compensating transactions; Durable Functions |
| **Outbox** | Transactional event publishing | Write business change + outbox in one local transaction, relay to broker |
| **Queue-Based Load Leveling** | Smooth bursty load | Service Bus + Competing Consumers |

**WAF-recommended pairings:**
- Retry + Circuit Breaker
- Queue-Based Load Leveling + Competing Consumers
- Saga built on Compensating Transaction
