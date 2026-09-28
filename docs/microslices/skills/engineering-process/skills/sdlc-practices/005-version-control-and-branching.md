---
id: skill-version-control-and-branching-eb2eac9257
purpose: version control and branching
source: src/vibey_tools/skills/plugins/engineering-process/skills/sdlc-practices/SKILL.md
requires: ["skill-development-practices-709fe97ccf"]
links: ["skill-testing-strategy-9d73af50bf"]
---

## Version Control and Branching

### Commit Discipline
- Atomic commits.
- **Conventional Commits**: feat/fix/docs/chore/refactor/test — enables semantic-release and changelog automation.

### Branching Strategies

| Strategy | Best For | Key Rule |
|---|---|---|
| **Trunk-Based Development** | Most software, DORA-supported default | Integrate to trunk ≥ daily; ≤3 active branches; feature flags decouple deploy from release |
| **GitFlow** | Versioned/released software (mobile, embedded, on-prem) | Release branches for specific version cycles |
| **GitHub Flow** | Web apps with continuous delivery | One main + short-lived branches |

**DORA finding**: "Elite performers who meet their reliability targets are 2.3 times more likely to use trunk-based development," in which "developers work in small batches and merge their work into a shared trunk frequently."

### Advanced Git Tools
- **Merge queues** (GitHub Merge Queue, GitLab Merge Trains): serialize integration at scale.
- **Stacked PRs** (Graphite, ghstack): keep changes small.
- **Monorepo tooling**: Nx, Turborepo, Bazel with affected-change detection.
- **Git internals**: reflog, interactive rebase, cherry-pick, bisect for bug-finding.

### Dependency Management
- **SemVer** (MAJOR.MINOR.PATCH).
- **Lock files**: pin transitive dependency trees; prevent the diamond dependency problem.
- **SCA/automation**: Dependabot, Renovate, Snyk.
- **SBOMs** (CycloneDX, SPDX): increasingly required by regulation (US EO 14028, EU Cyber Resilience Act).

---
