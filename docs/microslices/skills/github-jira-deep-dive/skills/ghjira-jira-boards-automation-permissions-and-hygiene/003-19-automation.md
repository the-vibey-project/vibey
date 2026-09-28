---
id: skill-19-automation-09e62e97a3
purpose: 19 automation
source: src/vibey_tools/skills/plugins/github-jira-deep-dive/skills/ghjira-jira-boards-automation-permissions-and-hygiene/SKILL.md
requires: ["skill-18-reports-a698f7b73c"]
links: ["skill-20-permissions-413e85f726"]
---

## §19. Automation

**⚠️ Jira Automation (rules: trigger → condition → action) is the highest-leverage feature
most teams under-use.**
```
⚠️ Transition parent when all subtasks are done
⚠️ Assign based on component; notify a Slack channel on blocker creation
⚠️ Comment and transition when a linked PR merges (§23)
⚠️ Escalate priority when an SLA is breached (§21)
⚠️ Sync fields between linked issues
⚠️ Flag stale issues automatically rather than by nagging
```
**⚠️ Watch for**: ⚠️ **rule loops (rule A triggers rule B triggers A — Jira has loop
detection, but design against it), execution limits on lower plans, and rules running as a
user whose permissions matter.**
**⚠️ Automation is usually the right answer to "we need people to remember to..."** —
**people won't; the rule will.**

---
