---
id: skill-14-team-managed-vs-company-managed-d309e6af98
purpose: 14 team managed vs company managed
source: src/vibey_tools/skills/plugins/github-jira-deep-dive/skills/ghjira-jira-configuration-workflows-and-jql/SKILL.md
requires: ["skill-13-jira-s-configuration-model-9d14dd9ecc"]
links: ["skill-15-workflows-and-statuses-ff21c9755c"]
---

## §14. ⚠️ Team-Managed vs Company-Managed

**⚠️ The most consequential decision when creating a Jira Cloud project, and it is made by
people who don't know it's consequential.**
```
⚠️ TEAM-MANAGED (formerly next-gen)
  + Configured BY THE TEAM, in the project, no admin needed
  + Fast to set up, self-contained, easy to understand
  ⚠️ − Configuration is NOT shared or reusable across projects
  ⚠️ − Limited advanced features and cross-project reporting
  ⚠️ − Its custom fields are project-scoped, complicating global JQL

⚠️ COMPANY-MANAGED (formerly classic)
  + Shared schemes, consistency across many projects, full feature set
  + Better for portfolio reporting and org-wide standards
  ⚠️ − Requires a Jira admin for changes; slower to adapt
  ⚠️ − Shared schemes mean shared blast radius (§13)
```
**⚠️ Choosing badly is expensive**: ⚠️ **there is no clean in-place conversion between the
two — migration means moving issues between projects, with the associated loss of some
history and links.**
**⚠️ The rough guidance**: **independent team, wants autonomy, doesn't need cross-project
rollup → team-managed.** **Many teams needing consistent process, portfolio reporting, or
regulated workflow → company-managed.**

---
