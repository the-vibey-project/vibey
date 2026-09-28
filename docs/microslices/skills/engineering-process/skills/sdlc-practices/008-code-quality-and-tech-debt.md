---
id: skill-code-quality-and-tech-debt-54b22f1b74
purpose: code quality and tech debt
source: src/vibey_tools/skills/plugins/engineering-process/skills/sdlc-practices/SKILL.md
requires: ["skill-ci-cd-and-devops-83df6db94b"]
links: ["skill-release-and-operations-fe87400815"]
---

## Code Quality and Tech Debt

### Key Metrics
- **Cyclomatic complexity** (McCabe): concern threshold ~10–15.
- **Cognitive complexity** (SonarSource): better proxy for comprehensibility than cyclomatic.
- **Duplication**: jscpd, Simian, SonarQube.
- **Coupling/cohesion**: afferent/efferent, instability metric.
- **LCOM**: lack of cohesion of methods.

### Tech Debt Management
- **Fowler's quadrant**: deliberate/inadvertent × reckless/prudent.
- **SonarQube SQALE method**: quantifies debt ratio.
- Manage via ~20% capacity allocation, debt as first-class backlog items.
- **Boy Scout Rule**: leave code cleaner than you found it.
- **Strangler Fig pattern**: for legacy modernization.
- Feathers's *Working Effectively with Legacy Code*: characterization tests, seam identification.

### Code Review Culture
- Automate style/lint/security checks; reserve humans for design, logic, and intent.
- Keep PRs <400 LOC and review SLAs short — review lag is a measurable productivity drag.
- **Psychological safety**: non-personal feedback is prerequisite for effective review culture.

---
