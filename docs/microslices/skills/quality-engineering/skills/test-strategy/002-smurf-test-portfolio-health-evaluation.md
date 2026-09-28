---
id: skill-smurf-test-portfolio-health-evaluation-c360743786
purpose: smurf test portfolio health evaluation
source: src/vibey_tools/skills/plugins/quality-engineering/skills/test-strategy/SKILL.md
requires: ["skill-test-shape-models-match-your-architecture-642ec36b9c"]
links: ["skill-tdd-vs-bdd-vs-atdd-when-to-use-each-c76976e23a"]
---

## SMURF: Test Portfolio Health Evaluation

Google's SMURF framework (October 2024, Google Testing Blog) evaluates test portfolio health across five dimensions:

| Dimension | Evaluation Question | Healthy | Unhealthy |
|---|---|---|---|
| **Speed** | How fast is the suite? | Unit < 5 min; Full suite < 30 min | Any test blocking CI for > 1 hour |
| **Maintainability** | How easy to understand and change? | Test reads like documentation | Requires deep context to understand what's being tested |
| **Utilization** | How often are tests actually run? | All tests run on every PR | Significant tests only run on main or nightly |
| **Reliability** | How consistent are results? | < 2% flake rate per test | Retries regularly needed; "it passed on the retry" |
| **Fidelity** | How closely does the test simulate real usage? | Integration tests use real data formats and flows | Everything mocked; tests don't represent real behavior |

A test suite can score well on coverage while failing SMURF. A 90% coverage suite where half the tests are slow, flaky, and mock everything is worse than a 60% coverage suite where every test is fast, stable, and meaningful.

**Run a SMURF audit quarterly.** Each dimension can degrade independently without coverage numbers moving.

---
