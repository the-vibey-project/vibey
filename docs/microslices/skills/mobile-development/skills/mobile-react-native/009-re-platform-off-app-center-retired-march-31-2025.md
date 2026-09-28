---
id: skill-re-platform-off-app-center-retired-march-31-2025-9a1ae5aec4
purpose: re platform off app center retired march 31 2025
source: src/vibey_tools/skills/plugins/mobile-development/skills/mobile-react-native/SKILL.md
requires: ["skill-crash-observability-7be21867b0"]
links: ["skill-cross-cutting-9dec0f69b3"]
---

## Re-platform off App Center (retired March 31, 2025)

Visual Studio App Center was retired except for Analytics & Diagnostics (extended runway,
~June 2026 → end of March 2027 — confirm the live date). Replace its pillars:

| App Center function | Replacement |
|---|---|
| CI/CD builds | Azure DevOps Pipelines or GitHub Actions + Fastlane (certs in Azure Key Vault) |
| OTA | CodePush (standalone) or EAS Update with mandatory-update enforcement |
| Crash/perf | Sentry (or Crashlytics) |
| Analytics | Azure Monitor |
