---
id: skill-test-doubles-mock-vs-stub-vs-spy-vs-fake-08d5f98e2d
purpose: test doubles mock vs stub vs spy vs fake
source: src/vibey_tools/skills/plugins/quality-engineering/skills/test-strategy/SKILL.md
requires: ["skill-mutation-testing-validating-your-test-suite-93dbce25ed"]
links: ["skill-anti-patterns-1327788ce4"]
---

## Test Doubles: Mock vs. Stub vs. Spy vs. Fake

Understanding the distinction prevents over-mocking (London school trap) and under-isolation (integration test creep).

| Double | What It Is | When to Use |
|---|---|---|
| **Stub** | Returns canned responses; doesn't verify calls | Providing test data; avoiding real I/O |
| **Mock** | Verifies calls were made; has expected behavior | Verifying interactions with collaborators |
| **Spy** | Wraps real object; records calls for later assertion | Verifying calls on a real object you can't replace |
| **Fake** | Working implementation simplified for testing | In-memory database; fake email service |
| **Dummy** | Placeholder that's never called | Satisfying required parameters that aren't used |

### Decision Guide

```
Is this crossing an I/O boundary? (network, disk, external service)
  → YES: Use a stub or fake. Always.
  → NO: Do you need to verify the interaction happened?
         → YES: Use a mock (carefully)
         → NO: Use the real object
```

**Don't mock what you don't own.** If you're mocking `requests.get()` directly, you're coupling your tests to an implementation detail. Instead: wrap the HTTP call in your own `HttpClient` class and mock *that*.

**Fake vs. Mock for databases:**
- For unit tests: use an in-memory fake (dictionary-backed repository)
- For integration tests: use a real database in testcontainers
- Never mock your ORM/database driver directly — tests become lies

---
