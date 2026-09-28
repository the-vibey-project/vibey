---
id: skill-13-backup-dr-and-continuity-1f63342bae
purpose: 13 backup dr and continuity
source: src/vibey_tools/skills/plugins/it-infrastructure-governance/skills/itgov-endpoints-continuity-itsm-and-vendor-risk/SKILL.md
requires: ["skill-12-endpoint-management-and-patching-07c8f23464"]
links: ["skill-14-monitoring-and-logging-fb711fd2cd"]
---

## §13. Backup, DR and Continuity

```
RPO   ⚠️ how much data you can afford to lose  (drives backup FREQUENCY)
RTO   ⚠️ how long you can afford to be down    (drives RECOVERY ARCHITECTURE)
```
**⚠️ The 3-2-1 rule, extended for ransomware**: **3 copies, 2 media types, 1 offsite** —
and ⚠️ **1 immutable or air-gapped, and 0 errors on verification.** **Immutability is the
addition that matters now, because modern ransomware deliberately targets backups first
and encrypts or deletes them before the production data.**

> **⚠️ GOTCHA — an untested backup is not a backup, and this is the most reliably
> expensive lesson in IT operations.** ⚠️ **Restore testing is the only thing that proves
> backup works, and it routinely reveals: missing dependencies, undocumented restore
> order, credentials stored only in the system being restored, RTOs that are wildly
> optimistic, and backup jobs that reported success while capturing nothing.**
> **⚠️ Test restores on a schedule, and test a full-system restore, not just a file.**

**DR**: **hot/warm/cold sites**, **failover and failback** (⚠️ **failback is usually harder
than failover and is almost never rehearsed**), **runbooks**, ⚠️ **and dependency mapping —
because systems restore in an order, and discovering that order during an incident is
the worst time.**
**BCP** is broader than IT: people, facilities, suppliers, communications. ⚠️ **Note that
your incident communication plan probably depends on the systems that are down.**

---
