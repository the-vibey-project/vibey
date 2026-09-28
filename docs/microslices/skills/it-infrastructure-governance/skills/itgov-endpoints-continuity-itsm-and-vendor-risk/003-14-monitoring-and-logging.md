---
id: skill-14-monitoring-and-logging-fb711fd2cd
purpose: 14 monitoring and logging
source: src/vibey_tools/skills/plugins/it-infrastructure-governance/skills/itgov-endpoints-continuity-itsm-and-vendor-risk/SKILL.md
requires: ["skill-13-backup-dr-and-continuity-1f63342bae"]
links: ["skill-15-itsm-and-change-management-cb4cca018a"]
---

## §14. Monitoring and Logging

**Infrastructure monitoring, APM, log aggregation, SIEM.**
**⚠️ Log what matters for both operations and investigation**: **authentication successes
and failures, privilege use and elevation, configuration and policy changes, data access
for sensitive stores, and administrative actions.**
**⚠️ Retention is a compliance decision and a cost decision, and it is usually decided by
neither** — **set it deliberately.**
**⚠️ Log integrity matters for it to be evidence**: **an attacker who can edit logs has
erased the investigation**, so **forward logs off-host promptly and write-protect them.**
**Alert design** — ⚠️ **see a reporting reference §11: every alert names an action, and
alerts that are routinely ignored should be deleted rather than tolerated.**

---
