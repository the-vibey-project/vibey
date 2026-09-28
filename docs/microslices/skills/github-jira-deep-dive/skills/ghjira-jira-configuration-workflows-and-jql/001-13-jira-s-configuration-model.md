---
id: skill-13-jira-s-configuration-model-9d14dd9ecc
purpose: 13 jira s configuration model
source: src/vibey_tools/skills/plugins/github-jira-deep-dive/skills/ghjira-jira-configuration-workflows-and-jql/SKILL.md
requires: []
links: ["skill-14-team-managed-vs-company-managed-d309e6af98"]
---

## §13. ⚠️ Jira's Configuration Model

**⚠️ The thing that makes Jira administration hard: a project's behaviour comes from
several SCHEMES that are often SHARED between projects.**
```
PROJECT
 ├─ ⚠️ Issue type scheme         which types exist
 ├─ ⚠️ Workflow scheme           type → workflow mapping
 ├─ ⚠️ Screen scheme             which fields appear, when
 ├─ ⚠️ Field configuration scheme  required/optional, hidden
 ├─ ⚠️ Permission scheme         who can do what
 ├─ ⚠️ Notification scheme       who gets emailed
 └─ ⚠️ Issue security scheme     who can SEE issues
```
> **⚠️ GOTCHA — schemes are shared by default, and this is the number one cause of
> accidental Jira damage.** ⚠️ **Editing a workflow or scheme "for one project" changes
> every project using it**, **often dozens, often without warning that matters.**
> **⚠️ ALWAYS check what else uses a scheme before editing.** **Copy the scheme and modify
> the copy if the change is genuinely project-specific — accepting that this adds to
> configuration debt** (§22 → `ghjira-jira-boards-automation-permissions-and-hygiene`).

**⚠️ Custom fields are the other trap**: ⚠️ **each one has a global performance cost, they
accumulate relentlessly, near-duplicates proliferate ("Team", "Team Name", "Owning
Team"), and they are painful to remove once populated.** **⚠️ Reuse before creating.**

---
