---
id: skill-22-misconceptions-6ceb4cacbe
purpose: 22 misconceptions
source: src/vibey_tools/skills/plugins/it-infrastructure-governance/skills/itgov-reference/SKILL.md
requires: ["skill-21-what-moved-verified-august-2026-8c0fdd1272"]
links: ["skill-23-numbers-e20e92e702"]
---

## §22. Misconceptions

| Misconception | Correction |
|---|---|
| The network perimeter is the security boundary | ⚠️ **Identity is. Every access decision happens there** (§0 → `itgov-infrastructure-layers-compute-storage-and-networking`, §6 → `itgov-directory-authentication-authorization-and-privileged-access`) |
| The domain is the AD security boundary | ⚠️ **The FOREST is** (§5 → `itgov-directory-authentication-authorization-and-privileged-access`) |
| All MFA is roughly equivalent | ⚠️ **Only phishing-resistant methods survive relay attacks** (§6 → `itgov-directory-authentication-authorization-and-privileged-access`, §21.1) |
| SMS MFA is adequate | ⚠️ **Weakest in use, and being retired** (§6 → `itgov-directory-authentication-authorization-and-privileged-access`, §21.1) |
| RAID protects your data | ⚠️ **Against drive failure only. Not deletion or ransomware** (§3 → `itgov-infrastructure-layers-compute-storage-and-networking`) |
| Snapshots are backups | ⚠️ **Same storage, same fate** (§3 → `itgov-infrastructure-layers-compute-storage-and-networking`, §13 → `itgov-endpoints-continuity-itsm-and-vendor-risk`) |
| The backup job says success | ⚠️ **Only a restore test proves it** (§13 → `itgov-endpoints-continuity-itsm-and-vendor-risk`) |
| RBAC solves access governance | ⚠️ **Role explosion is the default outcome without design** (§7 → `itgov-directory-authentication-authorization-and-privileged-access`) |
| ABAC is the more modern answer | ⚠️ **Trades role explosion for less-visible policy explosion** (§7 → `itgov-directory-authentication-authorization-and-privileged-access`) |
| Effective permissions can be read off the ACL | ⚠️ **Not with nested groups. Use tooling** (§7 → `itgov-directory-authentication-authorization-and-privileged-access`) |
| Recertification means access is controlled | ⚠️ **Rubber-stamping produces perfect evidence of nothing** (§10 → `itgov-identity-lifecycle-access-review-and-segregation-of-duties`) |
| Deprovisioning is handled by disabling the AD account | ⚠️ **Non-SSO apps, API keys and shared secrets persist** (§9 → `itgov-identity-lifecycle-access-review-and-segregation-of-duties`) |
| Role changes are a provisioning event | ⚠️ **They must trigger REVOCATION review — this is where creep comes from** (§9 → `itgov-identity-lifecycle-access-review-and-segregation-of-duties`) |
| SoD can be checked per permission | ⚠️ **It's combinatorial, over effective access** (§11 → `itgov-identity-lifecycle-access-review-and-segregation-of-duties`) |
| Zero-days are the main exploitation route | ⚠️ **Known, patchable vulnerabilities dominate** (§12 → `itgov-endpoints-continuity-itsm-and-vendor-risk`) |
| Compliance means secure | ⚠️ **It's a negotiated floor** (§17 → `itgov-endpoints-continuity-itsm-and-vendor-risk`) |
| Service accounts are a minor cleanup task | ⚠️ **They're the classical form of §21.2's problem** (§8 → `itgov-directory-authentication-authorization-and-privileged-access`) |
| AI agents created the machine identity problem | ⚠️ **They accelerated a decades-old one** (§21.2) |
| NHI ratios are established facts | ⚠️ **Mostly vendor-sourced, 25:1 to 144:1. Trust the direction** (§21.2) |
| Vaulting secrets solves NHI risk | ⚠️ **Eliminating static secrets does. Vaulting manages** (§21.2) |

---
