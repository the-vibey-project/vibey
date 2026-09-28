---
id: skill-part-3-github-atlassian-integration-efa2182f68
purpose: part 3 github atlassian integration
source: src/vibey_tools/skills/plugins/devsecops-cicd/skills/github-atlassian/SKILL.md
requires: ["skill-part-2-atlassian-cc9b251323"]
links: ["skill-part-4-cross-cutting-concerns-a623125fdd"]
---

## Part 3 — GitHub ↔ Atlassian Integration

### The Official "GitHub for Jira" App

- Atlassian-maintained; **Jira Cloud only**
- Links commits/branches/PRs/builds/deployments to issues by string-matching the Jira issue key
- Surfaces data in the Jira development panel, board card icons, Code/Releases/Deployments tabs, JQL
- Smart commits: `PROJ-123 #comment ... #time 2h #done`
- "Create branch" button in Jira; JQL queries over development data

**Limitation:** only as reliable as naming discipline — which is why mature teams enforce issue-keyed branch names via rulesets and drive status transitions via Actions.

**GitHub Enterprise Server ↔ Jira DC:** not supported by the native app — requires third-party (e.g., GitKraken's Git Integration for Jira).

### Production Integration Pattern (50–500 Engineers)

1. **Enforce issue-keyed branch names** via GitHub rulesets (regex rejecting non-conforming branches at push)
2. **Drive Jira status transitions from GitHub Actions** on `pull_request`/`push`/deployment events calling the Jira API or `atlassian/gajira-*` actions — more reliable than smart commits (which depend on developer discipline and email matching)
3. **Track deployments** via GitHub Environments → Jira deployment panel
4. **Pipe CodeQL/Dependabot findings into Jira** as security issues via Actions for SLA-tracked remediation
5. **Keep Jira as system of record;** use GitHub Projects only for engineering-local sprint views to avoid dual-maintenance

---
