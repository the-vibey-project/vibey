---
id: skill-observability-tie-in-32be950088
purpose: observability tie in
source: src/vibey_tools/skills/plugins/mobile-development/skills/mobile-azure-deployment/SKILL.md
requires: ["skill-ci-cd-after-app-center-retired-march-31-2025-49e257290b"]
links: ["skill-recommended-staging-1f9166e358"]
---

## Observability tie-in

Crash via Sentry / Crashlytics; performance via New Relic Mobile / Dynatrace / Firebase Performance;
**OpenTelemetry → Azure Monitor Application Insights** (`@azure/monitor-opentelemetry-exporter`).
Hermes lacks OTel auto-instrumentation, so create spans manually and correlate to backend traces via
**W3C Trace Context**. (See `mobile-react-native` for RN-side wiring.)
