---
id: skill-part-16-migration-anti-patterns-5dacdb26d4
purpose: part 16 migration anti patterns
source: src/vibey_tools/skills/plugins/security-first-dev/skills/codebase-modernization/SKILL.md
requires: ["skill-part-15-things-to-never-do-during-modernization-50c770066b"]
links: []
---

## PART 16: MIGRATION ANTI-PATTERNS

**The "big bang" anti-pattern:** Attempting to migrate all authentication, fix all SQL injection,
restructure all layers, add the DevSecOps pipeline, and write all missing tests in a single
sprint. Produces a PR nobody can safely review.
*Correct approach: One phase per sprint. One component per PR.*

**The "fix it forward" anti-pattern:** Encountering a broken test and "fixing" it to make the
new code pass, without understanding why it was failing.
*Correct approach: Understand the failure. If your change is correct and the test was wrong,
update the test and document why.*

**The "security theater" anti-pattern:** Adding `[Authorize]` attributes while leaving the
middleware pipeline in the wrong order. The decorators exist; the authorization does nothing.
*Correct approach: Verify the middleware pipeline order before declaring auth migration complete.*

**The "abandoned strangler" anti-pattern:** Starting a component migration but not completing it
— leaving both old and new implementation with unclear authority.
*Correct approach: Remove old code in the same PR that verifies the new code works.*

**The "coverage inflation" anti-pattern:** Writing tests with no assertions to achieve coverage
numbers.
*Correct approach: Coverage is a signal. A test without meaningful assertions is worse than no
test — it creates false confidence.*
