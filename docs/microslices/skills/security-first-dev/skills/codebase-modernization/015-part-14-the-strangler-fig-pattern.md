---
id: skill-part-14-the-strangler-fig-pattern-10e8056681
purpose: part 14 the strangler fig pattern
source: src/vibey_tools/skills/plugins/security-first-dev/skills/codebase-modernization/SKILL.md
requires: ["skill-part-13-migration-execution-protocol-9-steps-5a5749d311"]
links: ["skill-part-15-things-to-never-do-during-modernization-50c770066b"]
---

## PART 14: THE STRANGLER FIG PATTERN

Do not rewrite existing code wholesale. Use the strangler fig:

- New code is written to the full Security-First Scrum standard.
- Old code is migrated one component at a time, each PR fully tested.
- The old implementation is removed only after the new one is verified in production.
- Feature flags decouple migration from release — the new auth flow can be deployed but not
  activated until validated.

Every migration PR has a clear before and after state. The old code is removed in the same PR
that confirms the new code works. Never leave both old and new implementation in the codebase
simultaneously with unclear which one is authoritative.

---
