---
id: skill-tdd-vs-bdd-vs-atdd-when-to-use-each-c76976e23a
purpose: tdd vs bdd vs atdd when to use each
source: src/vibey_tools/skills/plugins/quality-engineering/skills/test-strategy/SKILL.md
requires: ["skill-smurf-test-portfolio-health-evaluation-c360743786"]
links: ["skill-consumer-driven-contract-testing-bf5fe2b3f9"]
---

## TDD vs. BDD vs. ATDD: When to Use Each

### Test-Driven Development (TDD)
**When to use:** Building new code where the design is uncertain. TDD drives good design by making you write tests first — the resulting code must be testable by construction.

**Cycle:** Red → Green → Refactor
1. Write a failing test (Red) — must fail for the right reason
2. Write minimum code to pass (Green) — no more, no less
3. Refactor — improve structure without breaking tests

**London School (Mockist):** Mock all collaborators; test in strict isolation. Best for legacy code with unclear boundaries.
**Chicago School (Classicist):** Use real objects; mock only I/O boundaries. Best for new code with well-defined domain.

**Not a good fit for:** exploratory work where the requirements themselves are unclear; UI testing; performance testing.

### Behavior-Driven Development (BDD)
**When to use:** When you want test specifications that non-technical stakeholders can read and verify. BDD tests document behavior in business language (Gherkin: Given/When/Then).

```gherkin
Scenario: Successful password reset
  Given a user with email "user@example.com" exists
  And the user has not reset their password in the last 24 hours
  When the user requests a password reset link
  Then an email is sent to "user@example.com" within 60 seconds
  And the link expires after 1 hour
```

**Best fit:** APIs with complex business rules; features where the business logic is the source of truth; scenarios with multiple stakeholders who need to agree on behavior.

**Not a good fit for:** Low-level technical code (use TDD instead); scenarios where Gherkin would be artificially verbose.

### Acceptance Test-Driven Development (ATDD)
**When to use:** When you need the entire team — developer, tester, and business analyst — to agree on behavior *before* development begins.

**Three Amigos:** Before writing any code, three roles collaborate:
1. **Business Analyst / Product Owner** — what is the business rule?
2. **Developer** — how will this be implemented? What are the edge cases?
3. **Tester** — what could go wrong? What are the negative scenarios?

Together they write Gherkin scenarios that become the acceptance criteria and the test suite simultaneously.

**Key distinction from BDD:** ATDD is a *process* (collaboration before development); BDD is a *format* (Gherkin syntax). You can do BDD without ATDD (writing scenarios after the fact) or ATDD without Gherkin (using plain English acceptance criteria).

---
