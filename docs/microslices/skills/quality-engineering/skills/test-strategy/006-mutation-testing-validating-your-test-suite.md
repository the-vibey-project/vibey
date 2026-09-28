---
id: skill-mutation-testing-validating-your-test-suite-93dbce25ed
purpose: mutation testing validating your test suite
source: src/vibey_tools/skills/plugins/quality-engineering/skills/test-strategy/SKILL.md
requires: ["skill-property-based-testing-with-hypothesis-00be087fe4"]
links: ["skill-test-doubles-mock-vs-stub-vs-spy-vs-fake-08d5f98e2d"]
---

## Mutation Testing: Validating Your Test Suite

Mutation testing introduces code mutations (changes to operators, conditions, return values) and verifies your tests catch them. It answers the question: "Do my tests actually detect bugs, or do they just run code?"

**Mutation score = killed mutants / total non-equivalent mutants × 100**

A mutation score below 60% means your tests have significant gaps — regardless of coverage percentage. High coverage + low mutation score = tests are checking behavior happened, not that it happened *correctly*.

### Tool Selection
- **mutmut** — simplest to use; good default choice for most Python projects
- **cosmic-ray** — more configurable; supports parallel execution; better for large codebases

### When to Run Mutation Testing
Mutation testing is **too slow for CI gates** on large codebases. Use it as:
- **Pre-release audit** — run on business-critical modules before major releases
- **Test quality assessment** — run when a bug escaped your test suite to understand why
- **Onboarding benchmark** — establish baseline mutation scores for new modules

**Don't gate PRs on mutation score** (too slow). Do track mutation scores in your quality metrics dashboard and investigate declining trends.

---
