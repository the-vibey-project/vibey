---
id: skill-crash-observability-7be21867b0
purpose: crash observability
source: src/vibey_tools/skills/plugins/mobile-development/skills/mobile-react-native/SKILL.md
requires: ["skill-azure-integration-auth-d34b7603cd"]
links: ["skill-re-platform-off-app-center-retired-march-31-2025-9a1ae5aec4"]
---

## Crash / observability

- **Sentry React Native SDK** (App Start, slow/frozen frames, Hermes profiling, session replay)
  is the leading App Center crash replacement; Firebase Crashlytics and Bugsnag are alternatives.
- Sentry propagates **W3C Trace Context** for end-to-end traces to the backend.
- **OpenTelemetry → Azure Monitor Application Insights** via `@azure/monitor-opentelemetry-exporter`.
  Caveat: **OTel auto-instrumentation does NOT work on Hermes/JSC** — create spans manually and
  correlate to backend traces via W3C Trace Context.
