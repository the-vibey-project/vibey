---
id: skill-5-directory-services-and-hybrid-identity-93641f1401
purpose: 5 directory services and hybrid identity
source: src/vibey_tools/skills/plugins/it-infrastructure-governance/skills/itgov-directory-authentication-authorization-and-privileged-access/SKILL.md
requires: []
links: ["skill-6-authentication-80e428ff60"]
---

## §5. Directory Services and Hybrid Identity

**⚠️ Active Directory remains the backbone of enterprise identity in most organizations**,
and it is not going away quickly.
```
FOREST / DOMAIN / OU     ⚠️ the FOREST is the security boundary, not the domain —
                         a common and consequential misunderstanding
GROUP POLICY (GPO)       configuration management for domain-joined machines
KERBEROS                 ⚠️ ticket-based; needs time sync and correct SPNs
LDAP                     directory queries
SITES AND SERVICES       replication topology
FSMO ROLES               ⚠️ single-master operations; know where they live
```
**⚠️ Tiered administration is the single most important AD security model**: **Tier 0
(identity infrastructure — domain controllers, AD, PKI), Tier 1 (servers and
applications), Tier 2 (workstations).** ⚠️ **Credentials must never flow downward: a
Domain Admin logging into a workstation exposes Tier 0 credentials to a Tier 2 machine,
and that single practice is how most domain compromises escalate.**

**Hybrid**: **directory synchronization to a cloud IdP**, **federation vs password hash
sync vs pass-through**, ⚠️ **and the cloud tenant and the on-prem forest are separate trust
domains that happen to share user objects.**
> **⚠️ GOTCHA — hybrid means your attack surface is the union, not the intersection.**
> ⚠️ **Compromise of on-prem AD frequently means compromise of the synced cloud identities,
> and sync accounts are themselves Tier 0 assets that are routinely under-protected.**
> **Legacy authentication protocols that bypass modern policy are the other standing
> hybrid gap** (§6, §21.1 → `itgov-reference`).

---
