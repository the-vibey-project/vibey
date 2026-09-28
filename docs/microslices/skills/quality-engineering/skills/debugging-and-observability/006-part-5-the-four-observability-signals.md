---
id: skill-part-5-the-four-observability-signals-cd3a363134
purpose: part 5 the four observability signals
source: src/vibey_tools/skills/plugins/quality-engineering/skills/debugging-and-observability/SKILL.md
requires: ["skill-part-4-opentelemetry-cncf-graduated-may-11-2026-4ef5a9c8ef"]
links: ["skill-part-6-ebpf-for-production-debugging-02daf74bfc"]
---

## Part 5 — The Four Observability Signals

The four signals complement each other:

| Signal | Purpose |
|--------|---------|
| **Metrics** | Numeric time-series — *alert you* |
| **Logs** | Discrete events with context — *explain what happened* |
| **Traces** | Request flow across services — *show where* |
| **Continuous Profiling** | CPU/memory/goroutine flame graphs in production — *show how much* |

### Distributed Tracing

A trace = trace ID + spans (span ID, parent, attributes, events, status).

Sampling strategies: head-based, tail-based (decide after outcome), adaptive.

**Backends:** Jaeger, Zipkin, Grafana Tempo, Honeycomb, Datadog APM, Azure Monitor, AWS X-Ray.

Always include trace ID + span ID in every log record for log↔trace correlation. The `otelslog` bridge (Go), WinstonInstrumentation, and Serilog Activity enrichment do this automatically.

### Continuous Profiling

Always-on, aggregated CPU/memory profiling in production for trend analysis and deploy-correlated regression detection. Overhead is typically under 1% at production sampling rates.

**Tools:** Parca (CNCF), Grafana Pyroscope, Google Cloud Profiler, Datadog Continuous Profiler.

### APM and Error Tracking

**APM:** Datadog APM (market leader), New Relic, Dynatrace, Elastic APM, Honeycomb (wide events, high cardinality, BubbleUp).

**Error tracking:**
- **Sentry** — dominant; unified errors+traces+replays+profiling+logs; free tier: 5,000 errors
- **Rollbar** — focused error tracking, aggressive grouping; free: 5,000 events/month
- **Bugsnag** — mobile/gaming strength, stability scores
- **Raygun** — deployment-correlated, RUM, user-impact prioritization

**Sentry Seer:** Runs RCA → Solution → Code Generation using issue context, traces, logs, and profiles. Vendor-reported "94.5% accuracy / 38,000+ issues helped" — not independently audited.

**AI observability assistants:**
- **Datadog Watchdog RCA** — automatically identifies causal relationships between symptoms and pinpoints root cause; no configuration required
- **Dynatrace Davis AI** — deterministic, causation-based engine performing automatic fault-tree analysis across a real-time dependency graph; correlates events sharing a root cause into a single "problem"

---
