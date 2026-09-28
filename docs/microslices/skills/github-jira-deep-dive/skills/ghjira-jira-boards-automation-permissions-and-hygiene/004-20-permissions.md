---
id: skill-20-permissions-413e85f726
purpose: 20 permissions
source: src/vibey_tools/skills/plugins/github-jira-deep-dive/skills/ghjira-jira-boards-automation-permissions-and-hygiene/SKILL.md
requires: ["skill-19-automation-09e62e97a3"]
links: ["skill-21-jira-service-management-c4c3f6fbcd"]
---

## §20. Permissions

**⚠️ Three distinct layers that get confused:**
```
⚠️ GLOBAL permissions       site-level (who can administer)
⚠️ PROJECT permission scheme  who can browse, create, edit, transition,
   assign, comment, delete within a project
⚠️ ISSUE SECURITY scheme    who can SEE individual issues — used for
   sensitive work (HR, security, legal) inside an otherwise open project
```
**⚠️ Plus filter/dashboard sharing permissions, which are separate again** (§16 → `ghjira-jira-configuration-workflows-and-jql`) —
⚠️ **and the classic confusion is "why can't they see the board?" when the answer is the
underlying FILTER isn't shared.**
**⚠️ Grant via GROUPS or PROJECT ROLES rather than individuals** — ⚠️ **roles are the more
maintainable choice because they're per-project and can be populated by the project lead
without an admin.**

---
