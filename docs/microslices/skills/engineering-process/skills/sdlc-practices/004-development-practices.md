---
id: skill-development-practices-709fe97ccf
purpose: development practices
source: src/vibey_tools/skills/plugins/engineering-process/skills/sdlc-practices/SKILL.md
requires: ["skill-architecture-as-a-continuous-concern-05f42ce907"]
links: ["skill-version-control-and-branching-eb2eac9257"]
---

## Development Practices

### Code Quality Enforcement
- **Linters**: ESLint, Pylint, Checkstyle.
- **Formatters**: Prettier, Black, gofmt.
- **Static analysis**: part of the CI pipeline.

### Code Review — Empirical Guidance
The SmartBear/Cisco study (~2,500 reviews, 3.2M LOC, 10 months) found:
- Review **fewer than 200–400 LOC at a time**.
- Spread the review over **no more than 60–90 minutes**.
- At this size: **70–90% defect-detection yield**.
- Defect detection drops sharply beyond ~400 LOC.
- **Author pre-annotation** measurably reduces defects.

**Common dysfunctions**: nitpick theater, rubber-stamping, PRs blocked for weeks. Google's guidelines emphasize splitting large CLs.

### Test-Driven Development (TDD)
Red-Green-Refactor cycle. Evidence:
- Nagappan et al. (Microsoft/IBM) found pre-release defect-density reductions of **40–90%** with a **15–35%** increase in initial development time.
- Meta-analyses (Rafique & Mišić; Bissi et al.) confirm moderate quality benefit with inconclusive productivity effects.
- TDD's quality benefit is well-supported; productivity effect is not.

### Pair and Mob Programming
- **Pair programming** (Hannay et al. meta-analysis): *small* positive effect on quality, *medium* positive effect on duration (speed), *medium negative* effect on effort. Faster on simple tasks, higher-quality on complex tasks, costs more total person-hours.
- **Mob/ensemble programming**: excels for complex, high-knowledge-transfer work.

### Refactoring
- Fowler's catalog (2nd ed.) tied to code smells.
- Kent Beck's *Tidy First?* (2023): separate structural "tidyings" from behavioral changes as economic options.

---
