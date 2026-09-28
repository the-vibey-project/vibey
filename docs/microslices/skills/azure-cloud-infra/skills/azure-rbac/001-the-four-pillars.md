---
id: skill-the-four-pillars-4289b75200
purpose: the four pillars
source: src/vibey_tools/skills/plugins/azure-cloud-infra/skills/azure-rbac/SKILL.md
requires: []
links: ["skill-control-plane-vs-data-plane-the-1-production-incident-source-858cc7ef54"]
---

## The Four Pillars

Every Azure RBAC operation resolves to four interlocking concepts:

1. **Security principal** — the identity requesting access. Four types:
   - **User** — individual Entra ID profile (including B2B guests)
   - **Group** — Entra ID group; role assignments are transitive through nested groups
   - **Service principal** — application identity for code and automation
   - **Managed identity** — Azure-managed service principal with automatic credential lifecycle

2. **Role definition** — a named collection of permissions specifying allowed operations at control and data planes. Azure ships 250+ built-in roles; tenants can create up to 5,000 custom roles.

3. **Scope** — the boundary where access applies. Strict hierarchy: **management group → subscription → resource group → resource**. Permissions cascade downward automatically.

4. **Role assignment** — binds one role definition to one security principal at one scope. Permissions are the additive union of all assignments. There is no implicit deny.

---
