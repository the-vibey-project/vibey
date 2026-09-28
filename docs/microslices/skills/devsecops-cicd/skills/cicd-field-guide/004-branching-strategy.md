---
id: skill-branching-strategy-a377b868dd
purpose: branching strategy
source: src/vibey_tools/skills/plugins/devsecops-cicd/skills/cicd-field-guide/SKILL.md
requires: ["skill-platform-selection-1a8ec9df4f"]
links: ["skill-security-the-highest-leverage-action-d281b75233"]
---

## Branching Strategy

### The Evidence-Backed Default: Trunk-Based Development (TBD)

DORA research (based on 33,000+ professionals) identifies TBD as a key predictor of elite performance. Atlassian now labels GitFlow a "legacy workflow"; GitFlow's creator recommends against it for continuous delivery.

| Strategy | When to Use |
|---|---|
| **Trunk-based development** | SaaS/web apps, strong CI/CD, continuous deployment — **the default** |
| **GitHub Flow** (main + short-lived feature branches) | Pragmatic middle ground for web teams wanting PR review without GitFlow complexity |
| **GitFlow** | Versioned/released software — mobile apps, desktop/firmware, OSS with external contributors, heavy-compliance |

**The most common, well-documented anti-pattern:** long-lived feature branches — they drift from trunk, compound merge conflicts, and defeat true continuous integration.

**Tooling solutions:**
- **Merge queues** (GitHub merge queue, GitLab merge trains): build speculative merge commits to keep main green at scale
- **Stacked PRs** (Graphite): decompose large changes while keeping PRs reviewable

---
