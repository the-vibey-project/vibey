---
id: skill-part-3-triage-priority-system-e89e7ec4d1
purpose: part 3 triage priority system
source: src/vibey_tools/skills/plugins/security-first-dev/skills/codebase-modernization/SKILL.md
requires: ["skill-part-2-modernization-prime-directive-1f99f5803e"]
links: ["skill-part-4-phase-0-codebase-assessment-run-before-touching-anything-8b8d8c01be"]
---

## PART 3: TRIAGE PRIORITY SYSTEM

When a codebase has multiple issues, address them in this order. Do not reorder based on what
seems more interesting or architectural.

| Priority | Category | Rationale |
|---|---|---|
| **P0 — Immediate** | Hardcoded secrets / credentials in source code | Active exposure. Every minute counts. |
| **P0 — Immediate** | Broken or missing authentication on production endpoints | Active exploitation surface. |
| **P1 — This Sprint** | SQL injection / non-parameterized queries | High CVSS; straightforward fix. |
| **P1 — This Sprint** | `localStorage` token storage in React | XSS + token theft = full account compromise. |
| **P1 — This Sprint** | Missing or permissive CORS (`AllowAnyOrigin`) | Cross-origin attack surface on production. |
| **P2 — Next Sprint** | Implicit Grant auth flow still in use | Deprecated; migration is planned work. |
| **P2 — Next Sprint** | Connection strings with keys (replace with Managed Identity) | High value; requires infra coordination. |
| **P2 — Next Sprint** | Missing rate limiting on public endpoints | Abuse surface; not currently exploited. |
| **P3 — Backlog** | Architecture violations (business logic in controllers, etc.) | Quality debt; not an active security risk. |
| **P3 — Backlog** | Missing test coverage on non-security paths | Quality debt; address incrementally. |
| **P3 — Backlog** | Missing XML doc comments / docstrings | Documentation debt. |

---
