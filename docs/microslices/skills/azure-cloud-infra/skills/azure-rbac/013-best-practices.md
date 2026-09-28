---
id: skill-best-practices-f274b432f9
purpose: best practices
source: src/vibey_tools/skills/plugins/azure-cloud-infra/skills/azure-rbac/SKILL.md
requires: ["skill-azure-rbac-vs-entra-id-roles-6beed49c87"]
links: ["skill-auditing-kql-queries-b03929eed4"]
---

## Best Practices

**Security principals:**
- Always assign roles to groups, not individual users (reduces assignment count, simplifies onboarding/offboarding)
- Prefer user-assigned managed identities over service principals for Azure workloads
- Use system-assigned managed identities only when permissions should be tied to the resource lifecycle

**Privileged access:**
- Limit Owner to 3 or fewer per subscription
- Use PIM eligible assignments for all privileged roles (Owner, User Access Administrator, Contributor at subscription scope)
- Classic admin roles are retired — do not use

**Role design:**
- Use `Role Based Access Control Administrator` over `User Access Administrator` when delegating RBAC management — it supports ABAC conditions preventing privilege escalation
- Use groups over individuals to maximize the value of each role assignment against the 4,000 limit
- Use explicit action strings (not wildcards) for security-sensitive custom roles — wildcards automatically include future operations Microsoft adds to a provider

**ABAC conditions** (GA for Blob and Queue Storage): replace thousands of per-resource assignments with a single conditional assignment scoped by blob index tags, container names, or blob paths.

---
