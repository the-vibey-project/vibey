---
id: skill-assessing-test-suite-health-diagnostic-questions-2047556988
purpose: assessing test suite health diagnostic questions
source: src/vibey_tools/skills/plugins/quality-engineering/skills/test-strategy/SKILL.md
requires: ["skill-security-testing-integration-a3cc83ba37"]
links: ["skill-test-strategy-document-one-page-template-2416aa5af8"]
---

## Assessing Test Suite Health: Diagnostic Questions

Use these questions to diagnose an existing test suite before recommending improvements:

**Coverage and Distribution**
- What is the current line coverage? Branch coverage? (Branch coverage reveals ~25% more untested paths)
- What is the distribution of unit vs. integration vs. E2E tests?
- Does the distribution match the architecture (pyramid for monolith, trophy for API, honeycomb for microservices)?

**Speed and Reliability**
- How long does the full test suite take to run?
- What is the flake rate? (Target < 2% per test; > 2% requires immediate attention)
- Are there tests that only run in CI, not locally?

**Confidence**
- When tests pass, do developers feel confident deploying?
- How many production bugs were caught by tests vs. escaped to production?
- Is there a mutation score for critical modules?

**Maintenance**
- When business logic changes, how many tests break that shouldn't?
- How long does it take to update tests after a refactor?
- Are there tests that test implementation rather than behavior?

**Integration and Contract**
- Do you have contract tests for all microservice boundaries?
- Do integration tests use real services (via testcontainers) or mocked responses?
- Are there any E2E tests that could be replaced with more reliable integration tests?

---
