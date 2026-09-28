---
id: skill-common-mistakes-and-production-incidents-03b560bef1
purpose: common mistakes and production incidents
source: src/vibey_tools/skills/plugins/azure-cloud-infra/skills/azure-rbac/SKILL.md
requires: ["skill-azure-cli-quick-reference-6a9569eb18"]
links: ["skill-azure-rbac-vs-entra-id-roles-6beed49c87"]
---

## Common Mistakes and Production Incidents

**1. Owner can't read blobs** — Owner and Contributor have zero data plane permissions. Always assign the appropriate data plane role alongside control plane roles. Storage Blob Data Contributor for blobs, Key Vault Secrets User for secrets.

**2. Propagation delays** — Role assignment changes take up to 10 minutes to propagate. Managed identities added to groups can take up to 24 hours. Add retry logic with 5–10 minute delays in CI/CD pipelines after role assignment creation.

**3. Missing `principalType` in IaC** — Omitting `principalType` in Bicep/ARM causes intermittent failures. Always specify it explicitly.

**4. Contributor can't deploy role assignments** — Creating `Microsoft.Authorization/roleAssignments` resources requires Owner or User Access Administrator. Contributor alone fails with `AuthorizationFailed`.

**5. Reader exposes too much** — Reader at subscription scope grants access to configurations, network topology, IP ranges, connection strings, and container images. Scope Reader to resource groups or use custom roles with only necessary read actions.

**6. Classic admin roles are retired** — Classic admin roles (Account Administrator, Service Administrator, Co-Administrator) retired August 31, 2024. Migrate to RBAC Owner and remove classic assignments.

**7. Cosmos DB data plane RBAC not in portal** — Cosmos DB's native data plane role assignments cannot be managed through the Azure portal. Use CLI, PowerShell, Bicep, or REST API.

**8. 4,000 limit per subscription** — Strategies: assign roles to groups not individuals, use PIM eligible assignments (don't count), assign at management group scope (don't count against per-sub limit), use ABAC conditions instead of per-resource assignments.

---
