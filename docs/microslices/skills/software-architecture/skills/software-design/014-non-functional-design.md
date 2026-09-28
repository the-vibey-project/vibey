---
id: skill-non-functional-design-b8a23c6331
purpose: non functional design
source: src/vibey_tools/skills/plugins/software-architecture/skills/software-design/SKILL.md
requires: ["skill-api-design-a88fb9e9ea"]
links: ["skill-ai-impact-on-software-design-6285a65681"]
---

## Non-Functional Design

### Performance
- Algorithmic complexity and data-structure/query decisions are the **hardest to fix later**
- Caching layers: client → CDN → application → database; invalidation is the hard part
- Async where complexity is justified; N+1 prevention; resource pooling

### Scalability
- Stateless design for horizontal scaling
- Partitioning/sharding for data
- Queue-based load leveling
- Scatter-gather for parallel reads
- **Cell-based architecture** for blast-radius isolation at extreme scale

### Resilience (Nygard, *Release It!*)
Design for failure. Key patterns:
- **Circuit Breaker:** "Hope is not a design method"
- **Timeouts:** The #1 missing protection against cascading failures
- **Bulkhead:** Isolated thread/connection pools — Netflix assigns isolated pools per dependency
- **Idempotency keys:** Prevent duplicate effects on retry
- **Saga + compensating transactions:** For distributed transactions
- **Health/ready/live endpoints:** For Kubernetes and orchestration platforms

**2025 research findings (arXiv 2512.16959):**
- Naive retry backoff without jitter "causes retry storms"
- "Transactional outbox + deduplication is the practical solution" to exactly-once delivery
- Hedging "cuts P99 latency by up to 40% but hurts throughput when capacity is tight"

### Security by Design
- **Threat modeling at design time** (STRIDE, trust boundaries on architecture diagrams)
- Least privilege throughout
- AuthN/AuthZ placement — enforce tenant context at a single chokepoint
- Encryption at rest and in transit
- Input validation defense-in-depth
- Secrets management (never in source control)
- **Zero-trust architecture** — recurring Thoughtworks Radar staple

### Observability
Design in from the start, not added later:
- **Correlation IDs** from the first request
- **RED method:** Rate, Errors, Duration (for services)
- **USE method:** Utilization, Saturation, Errors (for resources)
- Distributed tracing with span design and sampling strategy
- SLO-based alerting (not raw metrics thresholds)
- **OpenTelemetry** is the de-facto standard (vendor-neutral)

---
