---
id: skill-anti-patterns-1327788ce4
purpose: anti patterns
source: src/vibey_tools/skills/plugins/quality-engineering/skills/test-strategy/SKILL.md
requires: ["skill-test-doubles-mock-vs-stub-vs-spy-vs-fake-08d5f98e2d"]
links: ["skill-test-data-management-fa76c76ab6"]
---

## Anti-Patterns

### Testing Implementation, Not Behavior

**Bad:** Test that `UserService.__init__` calls `Repository.__init__` with specific parameters
**Good:** Test that creating a user through `UserService.create_user()` results in a user that can be retrieved

Tests should survive refactoring. If renaming an internal variable breaks a test, the test is testing the wrong thing.

### Brittle Tests

**Signs:** Tests break when unrelated code changes; tests depend on specific database row ordering; tests use hardcoded timestamps

**Fix:** Use domain-specific test data builders; avoid ordering dependencies; inject clocks and use `freezegun` for time-sensitive tests

### Slow Test Suites

**Signs:** Developers run tests "occasionally"; CI pipeline takes > 30 minutes; "I'll run tests later"

**Fix:** 
- Separate fast unit tests (run locally) from slow integration tests (run in CI)
- Parallelize with `pytest-xdist -n auto`
- Use `pytest -m "not slow"` for local development feedback loop
- Target: unit suite < 5 min, full suite < 30 min

### No Test Isolation

**Signs:** Tests pass in isolation, fail in sequence; tests leave data in databases; "works on my machine"

**Fix:**
- Each test owns its setup and teardown
- Use transaction rollback or container restart between tests (not manual cleanup)
- Never share mutable state between tests

### Coverage Anti-Patterns

**100% coverage target:** Causes trivial tests that don't verify behavior to be written. The coverage metric becomes gamed. Stop when you hit 100%, not when you've verified all behavior.

**Counting untested code as passing:** Missing a test for a critical path is not "acceptable coverage" — it's a risk.

**Fix:** Set a minimum floor (80% overall, 100% for critical paths). Track **coverage delta** on PRs to prevent regression. Focus investment on **behavior verification**, not percentage maximization.

---
