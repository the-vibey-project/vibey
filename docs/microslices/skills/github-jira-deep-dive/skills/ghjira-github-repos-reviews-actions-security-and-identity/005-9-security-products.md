---
id: skill-9-security-products-1dad34cbc8
purpose: 9 security products
source: src/vibey_tools/skills/plugins/github-jira-deep-dive/skills/ghjira-github-repos-reviews-actions-security-and-identity/SKILL.md
requires: ["skill-8-github-actions-0124609904"]
links: ["skill-10-issues-and-projects-502e136fab"]
---

## §9. Security Products

```
DEPENDABOT      ⚠️ alerts (vulnerable dependencies) · security updates ·
   version updates. ⚠️ Version updates generate a LOT of PRs — group them
   or you train the team to ignore Dependabot entirely
SECRET SCANNING ⚠️ detects committed credentials; PUSH PROTECTION blocks
   them before they land. ⚠️ Push protection is the high-value half
CODE SCANNING   ⚠️ CodeQL (semantic analysis) or third-party SARIF upload
DEPENDENCY REVIEW  ⚠️ diffs dependency changes in the PR
```
> **⚠️ GOTCHA — a leaked secret that has been pushed is compromised, full stop.**
> ⚠️ **Removing it from history does NOT undo the exposure** — **it may be in forks,
> caches, clones and logs.** **⚠️ ROTATE THE CREDENTIAL FIRST, then clean history if you
> want to.** **The order matters and people reliably get it backwards.**

**⚠️ Packaging changed substantially — see §26.2 → `ghjira-reference`**: **GHAS was unbundled into GitHub Secret
Protection and GitHub Code Security as separate products.**

---
