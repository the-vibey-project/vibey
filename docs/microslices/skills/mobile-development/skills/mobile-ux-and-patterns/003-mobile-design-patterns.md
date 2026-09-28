---
id: skill-mobile-design-patterns-81b7e03e06
purpose: mobile design patterns
source: src/vibey_tools/skills/plugins/mobile-development/skills/mobile-ux-and-patterns/SKILL.md
requires: ["skill-accessibility-is-now-a-legal-requirement-not-optional-171f33df18"]
links: ["skill-offline-first-persistence-libraries-7ad3214e06"]
---

## Mobile design patterns

- **Clean Architecture** layering: UI → Domain → Data.
- **MVVM/MVI** unidirectional flow.
- **Repository pattern** abstracting remote + local sources.
- **Offline-first** with sync + conflict resolution: last-write-wins vs operational/field-merge CRDT.
- **DI** via Hilt (Android) / TCA `@Dependency` or factory injection (iOS) — avoid the
  service-locator anti-pattern.
- **Feature flags / remote config** via Azure App Configuration or Firebase Remote Config.
- **Push architecture:** APNs + FCM unified behind **Azure Notification Hubs** (tags, templates,
  per-message telemetry). Note: FCM legacy API retired June 2024 — use **FCM v1**; APNs token auth
  required.
- **Background processing:** BGTaskScheduler (iOS) / WorkManager (Android) / `expo-background-task`.
- Result/sealed-class error types; REST vs GraphQL (persisted queries, N+1 mitigation); cursor-based
  pagination / infinite scroll.
