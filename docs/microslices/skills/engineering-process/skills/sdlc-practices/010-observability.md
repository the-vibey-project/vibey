---
id: skill-observability-c2dfad5042
purpose: observability
source: src/vibey_tools/skills/plugins/engineering-process/skills/sdlc-practices/SKILL.md
requires: ["skill-release-and-operations-fe87400815"]
links: ["skill-ai-assisted-development-2024-2026-2680760d69"]
---

## Observability

### Three (Plus One) Pillars
1. **Metrics**: time-series measurements; SLO-based/burn-rate alerting.
2. **Logs**: structured logging (JSON, correlation IDs).
3. **Traces**: distributed request tracing; W3C TraceContext propagation.
4. **Continuous profiling** (fourth pillar, emerging).

### OpenTelemetry (OTel)
The unified, vendor-neutral CNCF graduated standard (OTLP, semantic conventions, 90+ vendors). Spans traces/metrics/logs; profiling as a fourth signal. Replaces per-vendor agents.

### Alerting Philosophy
- **Symptom-based alerting over cause-based** — alert on user-visible impact, not internal indicators.
- Error tracking (Sentry, Rollbar, Bugsnag) integrated into the SDLC.
- Feature-flag-driven gradual rollouts double as observability tools.

---
