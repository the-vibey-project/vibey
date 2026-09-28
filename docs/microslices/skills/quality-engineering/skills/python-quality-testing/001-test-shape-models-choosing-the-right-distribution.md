---
id: skill-test-shape-models-choosing-the-right-distribution-8c550ebcea
purpose: test shape models choosing the right distribution
source: src/vibey_tools/skills/plugins/quality-engineering/skills/python-quality-testing/SKILL.md
requires: []
links: ["skill-smurf-evaluating-test-portfolio-health-e5e2ac8235"]
---

## Test Shape Models: Choosing the Right Distribution

The right test distribution depends on your architecture. Three dominant models:

### Test Pyramid (Cohn, 2009 / Fowler, 2012)
- **Wide unit base** → thin integration middle → narrow E2E top
- Best for: **monolithic applications** where unit isolation is cheap and informative
- Unit tests: fast, isolated, test single functions/classes
- Integration tests: test module interactions, database queries, API contracts
- E2E tests: test full user journeys; expensive, slow, flaky — use sparingly

### Testing Trophy (Kent C. Dodds)
- **Static analysis** (foundation) → unit tests (small layer) → **integration tests (largest layer)** → E2E (narrow top)
- Best for: **API-centric and frontend-heavy applications**
- Key insight: "The more your tests resemble the way your software is used, the more confidence they can give you" (Guillermo Rauch)
- Integration tests give the most confidence per test written for APIs

### Honeycomb (Spotify)
- **Integration tests dominate** — inter-service complexity is the primary risk
- Best for: **microservices architectures**
- Unit tests for pure business logic; integration tests for everything involving service boundaries
- E2E tests minimal — too brittle and slow across many services

### Swiss Cheese Model (James Reason, 1990)
Each layer — static analysis, unit, integration, contract, E2E, production monitoring — has holes. Defects escape to production only when holes **align across all layers**. Use this model for risk conversations with stakeholders: "We need contract tests because our integration tests can't catch provider breaking changes."

---
