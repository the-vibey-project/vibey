---
id: skill-three-pillars-one-05092001b0
purpose: three pillars one
source: src/vibey_tools/skills/plugins/software-architecture/skills/architecture-patterns/SKILL.md
requires: ["skill-high-availability-b781d238b7"]
links: ["skill-azure-mapping-994a1e3674"]
---

## Three Pillars + One
- **Metrics**: numeric time-series, cheap, alertable
- **Logs**: discrete events, structured JSON preferred, expensive at scale
- **Traces**: distributed request tracing, spans, **W3C Trace Context** propagation
- **Profiles** (fourth pillar): CPU/memory flame graphs

**OpenTelemetry (OTel)** is the unifying standard (collector, SDK, semantic conventions).
