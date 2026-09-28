---
id: skill-part-13-testing-for-debuggability-66932570f0
purpose: part 13 testing for debuggability
source: src/vibey_tools/skills/plugins/quality-engineering/skills/debugging-and-observability/SKILL.md
requires: ["skill-part-12-advanced-debugging-tools-55f1401baf"]
links: ["skill-part-14-customer-issue-triage-e857987992"]
---

## Part 13 — Testing for Debuggability

Tests are debugging tools: a focused failing test pinpoints exactly what broke.

- Use descriptive names (`should_throw_when_X`)
- Prefer one logical assertion per test
- Write assertion messages that explain the failure without reading the test
- Good assertion libraries: AssertJ (Java), FluentAssertions (.NET), pytest's introspecting asserts, Jest's diff output
- Snapshot testing catches unexpected output changes

### Mutation Testing

Finds tests that pass even when code is broken:
- PIT (Java)
- Stryker (JS/TS)
- mutmut (Python)

Mutation score is a signal of test suite quality.

### Property-Based Testing

Generates edge cases automatically and **shrinks** failures to a minimal example (automating MRE creation):
- Hypothesis (Python)
- fast-check (JS)
- QuickCheck (Haskell)

Stateful variants find state-dependent bugs.

---
