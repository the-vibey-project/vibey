---
id: skill-part-2-modernization-prime-directive-1f99f5803e
purpose: part 2 modernization prime directive
source: src/vibey_tools/skills/plugins/security-first-dev/skills/codebase-modernization/SKILL.md
requires: ["skill-part-1-three-laws-unchanged-always-in-this-order-25a5e3a1fc"]
links: ["skill-part-3-triage-priority-system-e89e7ec4d1"]
---

## PART 2: MODERNIZATION PRIME DIRECTIVE

Before touching any file:

1. Run the Phase 0 assessment protocol. Understand what you are walking into.
2. Confirm the scope of this specific task with the human. Scope creep during migration breaks
   things.
3. Identify whether the change is security-critical (Phase 1-3), architectural (Phase 4-5), or
   operational (Phase 6-8). Do not mix phases in a single PR.
4. Verify existing tests pass before you start. You own the baseline. If they were already broken,
   surface that immediately — do not inherit a broken build silently.
5. Make your change. Re-run tests. The codebase must be passing when you are done.

**The iron rule of modernization:** every PR leaves the codebase more secure and working than
before. A PR that improves architecture but introduces a regression is not acceptable. A PR that
removes a vulnerability but breaks auth is not acceptable.

**Stop and surface to the human when:**
- You discover a vulnerability outside the scope of the current task (log it; do not fix it
  unilaterally)
- The existing code has no tests and adding the security control requires refactoring untested code
- A dependency is so outdated that upgrading it would require cascading changes beyond sprint scope
- You find hardcoded credentials — rotate them before doing anything else (Phase 1)

---
