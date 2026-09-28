---
id: skill-caveats-b51642095f
purpose: caveats
source: src/vibey_tools/skills/plugins/okta-workflows/skills/okta-workflows-field-guide/SKILL.md
requires: ["skill-recent-platform-changes-2025-2026-d2c6e03cc2"]
links: []
---

## Caveats

- Okta Workflows is a continuously updated SaaS with no discrete version numbers; specific card
  behaviors (especially the "tip-bug" 1.3 and fixed OKTA-xxxxx items) may already differ in the
  target org. Validate each quirk in the Ionis sandbox before relying on a workaround.
- The Tables concurrent-write race condition (3.5) is an inference from the documented read-then-write
  upsert pattern, not an explicitly documented bug — **labeled THEORY**.
- No confirmed public bug report was found for APP_GROUP/OKTA_GROUP filtering misbehavior, nor for
  the Entra Search Group Members card silently dropping paginated results beyond its documented
  900-record cap — **treat those specific claims as UNCONFIRMED**.
- Latency has no SLA (Workflows is multi-tenant) and execution can vary 10x or more. Do not build
  hard timing assumptions into sync reconciliation logic.
- Two concurrency figures coexist and are easily confused: the **Okta connector** limit (30
  concurrent Workflows → org requests) versus the **org-wide** API concurrency limit (default 75
  simultaneous transactions, tracked separately for M365 vs. other traffic). Confirm which governs
  each card path.
