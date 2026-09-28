---
id: skill-part-2-correlation-trace-ids-the-distributed-debugging-primitive-3d8a572a13
purpose: part 2 correlation trace ids the distributed debugging primitive
source: src/vibey_tools/skills/plugins/quality-engineering/skills/debugging-and-observability/SKILL.md
requires: ["skill-part-1-the-debugging-mindset-and-process-712bb7067b"]
links: ["skill-part-3-structured-logging-deb8d5dabc"]
---

## Part 2 — Correlation/Trace IDs: The Distributed Debugging Primitive

**Correlation IDs are the fundamental distributed-debugging primitive.** Every system should propagate them from day one.

- **Without them:** you can see *that* errors spiked
- **With them:** you can see the error came from one tenant on the canary in eu-west-1 with a specific feature flag enabled

Propagate request context through the call chain without threading parameters everywhere using per-language mechanisms:
- **Java:** MDC (Mapped Diagnostic Context)
- **Python:** `contextvars`
- **Node.js:** `AsyncLocalStorage`
- **Go:** `context` package

The **W3C TraceContext** standard propagates `traceparent`/`tracestate` headers across service boundaries.

**High-cardinality attributes are essential for root cause.** High-cardinality fields let you answer "is this affecting everyone, or only a specific subset?" — distinguishing a generic error spike from "the error spike is coming from user:8675309 on the canary deployment in eu-west-1 who has the new-checkout-flow feature flag enabled."

---
