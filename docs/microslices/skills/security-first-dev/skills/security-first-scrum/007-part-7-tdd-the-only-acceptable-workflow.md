---
id: skill-part-7-tdd-the-only-acceptable-workflow-6b511246bb
purpose: part 7 tdd the only acceptable workflow
source: src/vibey_tools/skills/plugins/security-first-dev/skills/security-first-scrum/SKILL.md
requires: ["skill-part-6-onion-architecture-strict-layer-rules-d550544859"]
links: ["skill-part-8-middleware-pipeline-order-net-8-never-deviate-4c83a526e5"]
---

## PART 7: TDD — THE ONLY ACCEPTABLE WORKFLOW

```
RED      -> Write a failing test that expresses desired behaviour (including security behaviour).
GREEN    -> Write the minimum secure code to make the test pass. No more.
REFACTOR -> Improve code quality without changing observable behaviour.
SCAN     -> Run Semgrep on changed files.
COMMIT   -> Commit test + implementation together.
```

**Never write implementation code without a corresponding failing test.**
**Never commit code that lowers coverage below the threshold.**
**Every security control must have a test that proves it works AND a test that proves it blocks
the attack.**

### Security Test Mandate (Two Tests Per Control)

For every security control implemented, write two tests:
1. Positive test: legitimate request passes through correctly.
2. Negative/adversarial test: the attack vector is blocked.

```
// Examples
GetDocument_AuthenticatedOwner_Returns200WithDocument
GetDocument_AuthenticatedNonOwner_Returns403           // BOLA
CreateUser_ValidPayload_Returns201
CreateUser_SqlInjectionInName_Returns400
GetDocument_NoAuthToken_Returns401
GetDocument_ExpiredJwt_Returns401
```

### Coverage Requirements

- Overall: >= 80% line coverage (hard CI gate — fail below this).
- New code: >= 85% line coverage.
- Core business logic (services): >= 90%.
- Security-critical code paths (auth handlers, validators, input parsers): **100%**.

### Test Types

| Type | Scope | Speed | When |
|---|---|---|---|
| Unit | Single class | < 1 ms | Always first |
| Security Unit | Auth logic, validators | < 1 ms | Alongside unit |
| Integration | Multiple real components | Seconds | After unit |
| Contract | Schema / API boundary | Fast | Alongside contracts |
| E2E | Full system | Slow | For acceptance criteria |

### Test Naming Convention

**.NET (xUnit):** `MethodName_Scenario_ExpectedOutcome`
**Python/Databricks (pytest):** `test_<unit>_<scenario>_<expected_outcome>`
**React/Blazor (Vitest/bUnit):** `<Component> <scenario> <expected outcome>`

### Minimum Per Component

**Controllers:**
- Happy path: authenticated valid input → correct service call → correct output
- Unauthenticated → 401
- Authenticated, wrong role → 403
- Authenticated, wrong owner (BOLA) → 403
- Invalid schema → 400 (no service call made)
- Rate limit exceeded → 429

**Services:**
- Happy path for every public method
- Each branch / conditional has its own test
- Resource ownership: non-owner blocked
- Dependency failure modes

**Validators:**
- Every valid input variant passes
- SQL injection strings, XSS payloads, oversized inputs, null bytes, SSRF URLs — all fail

---
