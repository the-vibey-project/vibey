---
id: skill-7-authorization-rbac-and-beyond-c96b8d6948
purpose: 7 authorization rbac and beyond
source: src/vibey_tools/skills/plugins/it-infrastructure-governance/skills/itgov-directory-authentication-authorization-and-privileged-access/SKILL.md
requires: ["skill-6-authentication-80e428ff60"]
links: ["skill-8-privileged-access-f303acb628"]
---

## §7. Authorization: RBAC and Beyond

```
DAC   discretionary — the owner grants. ⚠️ How file shares become ungovernable
MAC   mandatory — system-enforced labels; military and SELinux
RBAC  ⚠️ permissions attach to ROLES, users get roles. The enterprise standard
ABAC  attribute-based — ⚠️ policy evaluated over user, resource, action, environment
ReBAC relationship-based — ⚠️ "can edit documents in projects they own" (Zanzibar-style)
PBAC  policy-based, often externalized to a decision engine
```
**⚠️ Core RBAC concepts**: **role hierarchies (inheritance), role assignment vs
activation, constraints, and permission aggregation.**
**⚠️ Least privilege** — grant the minimum required. **Need to know.** **Deny by default.**

> **⚠️ GOTCHA — role explosion is the standard failure of RBAC, and it is close to
> inevitable without design discipline.** ⚠️ **Every genuine exception becomes a new role;
> you end up with more roles than users, and nobody can say what any of them mean.**
> **The symptoms: roles named after individuals, roles nobody can define, and roles that
> exist only because one person needed one extra permission in 2019.**
>
> ⚠️ **The mitigations that work**: **separate BUSINESS roles (what a job does — these
> map to people) from TECHNICAL entitlements (what a system permits)**, so ⚠️ **one
> business role composes many entitlements and stays comprehensible.** **Add attributes
> for the dimensions that would otherwise multiply roles** — **department, location,
> clearance — rather than encoding them into role names.** **Run role mining against
> actual usage.** **And ⚠️ set an explicit retirement process, because roles are never
> removed unless someone owns removing them.**

**⚠️ RBAC vs ABAC in practice**: **RBAC is comprehensible, auditable, and coarse; ABAC is
expressive, fine-grained, and much harder to reason about or audit.** ⚠️ **The common
enterprise answer is hybrid — RBAC for the coarse grant, attributes for the conditions —
and a pure-ABAC deployment often trades role explosion for policy explosion, which is
worse because it's less visible.**
**⚠️ Group nesting** is where RBAC decays in Windows environments: **nested groups produce
effective permissions nobody can compute by inspection**, and ⚠️ **the only reliable
answer is tooling that resolves effective access rather than reading the ACL.**

---
