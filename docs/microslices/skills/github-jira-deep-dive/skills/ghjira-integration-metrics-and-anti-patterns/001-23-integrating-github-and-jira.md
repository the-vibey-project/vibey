---
id: skill-23-integrating-github-and-jira-1474eb96e8
purpose: 23 integrating github and jira
source: src/vibey_tools/skills/plugins/github-jira-deep-dive/skills/ghjira-integration-metrics-and-anti-patterns/SKILL.md
requires: []
links: ["skill-24-metrics-088aa36fcd"]
---

## §23. Integrating GitHub and Jira

**⚠️ The standard pattern is issue-key-in-branch-and-commit:**
```
⚠️ Branch name:   PROJ-123-short-description
⚠️ Commit message: PROJ-123 fix the thing
⚠️ PR title:      PROJ-123 Fix the thing
   → ⚠️ Jira shows linked branches, commits, PRs and builds on the issue
   → ⚠️ Smart commits can transition issues from the commit message
   → ⚠️ Automation can transition on PR open/merge (§19)
```
**⚠️ Why the convention matters more than the tooling**: ⚠️ **the entire integration hangs
on the issue key being present.** **Enforce it with a ruleset or a CI check rather than
with reminders.**
**⚠️ The genuine architectural question**: ⚠️ **which system is the source of truth for
STATUS?** **Having both means reconciliation, and the workable answers are either
"Jira, and GitHub events update it automatically" or "engineers live in GitHub, Jira is
generated."** **⚠️ What fails is asking people to update both manually.**
**⚠️ Do you need both?** ⚠️ **For a single engineering team with no service-desk or
portfolio needs, GitHub Issues and Projects may genuinely suffice** (§10 → `ghjira-github-repos-reviews-actions-security-and-identity`). **Jira earns its
place with multiple teams, non-engineering stakeholders, complex workflow requirements, or
ITSM** (§21 → `ghjira-jira-boards-automation-permissions-and-hygiene`).

---
