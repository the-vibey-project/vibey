---
id: skill-22-configuration-hygiene-a22f81a2c9
purpose: 22 configuration hygiene
source: src/vibey_tools/skills/plugins/github-jira-deep-dive/skills/ghjira-jira-boards-automation-permissions-and-hygiene/SKILL.md
requires: ["skill-21-jira-service-management-c4c3f6fbcd"]
links: []
---

## §22. ⚠️ Configuration Hygiene

**⚠️ Jira instances accumulate debt relentlessly and nobody is assigned to clean it.**
```
⚠️ Custom field sprawl — near-duplicates, unused fields, performance cost
⚠️ Workflow proliferation — dozens of nearly-identical workflows
⚠️ Orphaned schemes attached to nothing
⚠️ Statuses that mean the same thing with different names
⚠️ Dead automation rules and stale filters/dashboards
⚠️ Permission grants to people who left
```
**⚠️ The practices that work**: ⚠️ **a naming convention enforced from day one; a small
number of STANDARD workflows that projects adopt rather than each inventing one; a
periodic audit; a sandbox for testing configuration changes (⚠️ available on higher
plans, and worth it); and someone actually accountable for the instance.**
**⚠️ The hardest part is deletion** — ⚠️ **removing a populated custom field destroys its
data, so audits tend to produce lists nobody acts on.** **Prevent rather than remediate.**

---

# PART IV — TOGETHER
