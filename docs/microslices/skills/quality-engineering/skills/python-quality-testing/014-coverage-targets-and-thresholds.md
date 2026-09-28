---
id: skill-coverage-targets-and-thresholds-55251a4804
purpose: coverage targets and thresholds
source: src/vibey_tools/skills/plugins/quality-engineering/skills/python-quality-testing/SKILL.md
requires: ["skill-azure-devops-pipeline-for-python-68aa18180b"]
links: []
---

## Coverage Targets and Thresholds

| Code Category | Target | Rationale |
|---|---|---|
| Overall codebase | ≥ 80% | CI failure threshold |
| Critical paths (auth, payments, data access) | 100% | No uncovered path acceptable |
| New code on PRs | ≥ 80% delta | Prevent coverage regression |
| Generated code (migrations, DTOs) | Exempt | Not meaningful to test |

**Google's guidance:** 60% acceptable, 75% commendable, 90% exemplary. Set CI threshold at 80%.

**Coverage is a floor, not a goal.** A test that exercises a line without asserting anything increments coverage but adds no value. Focus test investment on behavior verification, not percentage maximization.
