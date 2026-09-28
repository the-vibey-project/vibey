---
id: skill-20-anti-patterns-fd49d45826
purpose: 20 anti patterns
source: src/vibey_tools/skills/plugins/it-infrastructure-governance/skills/itgov-reference/SKILL.md
requires: []
links: ["skill-21-what-moved-verified-august-2026-8c0fdd1272"]
---

## §20. Anti-Patterns

```
⚠️ Domain Admin used for daily work — Tier 0 credentials on Tier 2 machines (§5)
⚠️ Shared administrator accounts — no attribution, no accountability
⚠️ Service accounts with permanent passwords and excessive rights (§8)
⚠️ Nested groups nobody can resolve (§7)
⚠️ Roles named after people
⚠️ Access granted "temporarily" with no expiry
⚠️ Recertification as a rubber stamp (§10)
⚠️ Backups never restore-tested (§13)
⚠️ Snapshots or RAID treated as backup (§3, §13)
⚠️ Flat network with no segmentation (§4)
⚠️ Change process so heavy people route around it (§15)
⚠️ CMDB nobody trusts (§16)
⚠️ Break-glass accounts never tested (§6)
⚠️ Logs stored only on the host that generated them (§14)
⚠️ Legacy authentication left enabled "for one app" (§5, §21.1)
⚠️ Policy documents written for audit and never implemented (§17)
```

---
