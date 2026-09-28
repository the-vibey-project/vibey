---
id: skill-15-workflows-and-statuses-ff21c9755c
purpose: 15 workflows and statuses
source: src/vibey_tools/skills/plugins/github-jira-deep-dive/skills/ghjira-jira-configuration-workflows-and-jql/SKILL.md
requires: ["skill-14-team-managed-vs-company-managed-d309e6af98"]
links: ["skill-16-jql-d026e7494a"]
---

## §15. Workflows and Statuses

**⚠️ A workflow is statuses plus transitions, with four extension points that do the real
work:**
```
⚠️ CONDITIONS   who can SEE the transition button
⚠️ VALIDATORS   what must be TRUE to complete it (e.g. field required)
⚠️ POST FUNCTIONS  what happens AFTER (assign, set field, fire event)
⚠️ TRIGGERS     external events (e.g. a commit or PR) causing transition (§23)
```
**⚠️ Statuses are global objects; status CATEGORIES (To Do / In Progress / Done) drive
board columns and reporting** — ⚠️ **a status in the wrong category silently breaks
velocity and burndown, and it's a common misconfiguration.**
**⚠️ The design advice that actually matters**: ⚠️ **start with the simplest workflow that
could work and add only when a real failure demands it.** **Every extra status is a
handoff, a place work waits, and a thing people must remember to update** — ⚠️ **and a
workflow with fifteen statuses will be updated inaccurately, which destroys the reporting
it was built for** (§1 → `ghjira-git-data-model-branching-and-recovery`).

---
