---
id: skill-part-15-things-to-never-do-during-modernization-50c770066b
purpose: part 15 things to never do during modernization
source: src/vibey_tools/skills/plugins/security-first-dev/skills/codebase-modernization/SKILL.md
requires: ["skill-part-14-the-strangler-fig-pattern-10e8056681"]
links: ["skill-part-16-migration-anti-patterns-5dacdb26d4"]
---

## PART 15: THINGS TO NEVER DO DURING MODERNIZATION

### Never — They Make the Codebase Less Safe

- Disable or soft-fail a security gate to unblock a migration PR. Fix the finding.
- Remove `[Authorize]` from an endpoint to make a test pass. Fix the test infrastructure.
- Commit a "temporary" hardcoded secret while working out Key Vault integration. There is no
  temporary credential in git history.
- Rewrite authentication from scratch without testing every endpoint in the system.
- Mix architectural refactoring (Phase 4) with security fixes (Phase 1-3) in the same PR.
- Use `AllowAnyOrigin()` temporarily with a plan to tighten later. "Later" does not happen.
- Switch to `ManagedIdentityCredential` before the role assignment is confirmed in Azure.
- Disable public network access on a PaaS resource before a Private Endpoint is configured.
- Delete old authentication code before the new flow is verified working in staging.
- Set coverage gates at 80% on a 20% codebase. Set at current + 5%.
- Fix a vulnerability in a different component than the one tasked. Log it. Surface it.

### Never — They Violate People First

- Make infrastructure changes (Bicep, role assignments, network rules) without human confirmation.
- Rotate credentials autonomously. Credential rotation has organizational consequences.
- Scope-creep silently. Surface immediately when the task is larger than expected.
- Leave the human with a broken build. Stop, restore last working state, report what you found.

---
