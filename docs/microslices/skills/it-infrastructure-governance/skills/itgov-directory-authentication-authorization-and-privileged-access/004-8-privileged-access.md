---
id: skill-8-privileged-access-f303acb628
purpose: 8 privileged access
source: src/vibey_tools/skills/plugins/it-infrastructure-governance/skills/itgov-directory-authentication-authorization-and-privileged-access/SKILL.md
requires: ["skill-7-authorization-rbac-and-beyond-c96b8d6948"]
links: []
---

## §8. Privileged Access

**⚠️ Privileged accounts are the primary target in essentially every significant breach,
because they are the shortest path from foothold to objective.**
```
PAM VAULTING        ⚠️ credentials checked out, rotated after use, never known to humans
JUST-IN-TIME (JIT)  ⚠️ elevate for a window, then automatically revoke —
                    this eliminates STANDING privilege, which is the goal
SESSION RECORDING   privileged sessions recorded and reviewable
JEA / scoped admin  ⚠️ grant the specific task, not the admin role
TIERED ADMIN        §5
BREAK-GLASS         §6
```
**⚠️ Standing privilege is the thing to eliminate.** **A permanent Domain Admin is a
permanent target; a JIT-elevated one is a target for thirty minutes with an audit
trail.**
**⚠️ Service accounts are the perennial gap** — **shared, non-expiring passwords, excessive
privilege, no MFA possible, no owner, and nobody dares rotate them because nothing
documents what would break.** ⚠️ **This is §21.2 → `itgov-reference`'s problem in its classical form, and it
predates AI agents by decades.** **Managed service accounts, workload identities and
short-lived credentials are the structural fix.**
