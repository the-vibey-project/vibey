---
id: skill-9-resilience-patterns-ce5e37b7f5
purpose: 9 resilience patterns
source: src/vibey_tools/skills/plugins/design-patterns/skills/patterns-distributed-concurrency-and-messaging/SKILL.md
requires: ["skill-8-distributed-data-patterns-1e9acbef75"]
links: ["skill-10-concurrency-patterns-7ddc3dad7f"]
---

## §9. Resilience Patterns

**[DURABLE] These assume failure is normal, which in distributed systems it is.**

**Circuit Breaker** — after consecutive failures cross a threshold, stop sending requests
and fail fast, allowing the downstream to recover. Closed → open → half-open. **⚠️ Its real
purpose is preventing cascading failure**, and it belongs on any synchronous call to an
external dependency. ⚠️ **Notably under-adopted relative to how essential it is** — survey
work has found it substantially less used than API gateways in microservice deployments,
which weakens resilience in exactly the systems that need it.

**Retry with exponential backoff and jitter** — ⚠️ **jitter is not optional**;
synchronized retries are how you turn a blip into a thundering herd. **Only retry
idempotent operations, and only on transient failures.**

**Bulkhead** — isolate resource pools (separate connection pools or thread pools per
downstream) so one saturated dependency can't consume everything.

**Timeouts** — ⚠️ **the most under-set configuration in software.** An unbounded wait is a
resource leak with extra steps. **Every network call needs one.**

**Also**: **rate limiting / throttling**, **load shedding** (⚠️ **rejecting work early
beats collapsing under it**), **graceful degradation**, **dead letter queues**,
**health checks and readiness probes**, and the **Ambassador** pattern for putting retry,
logging, and monitoring beside the application rather than inside it.

**[DURABLE] The combination is what works**: timeout + retry with jitter + circuit breaker
+ bulkhead + fallback. Any one alone leaves a gap.

---
