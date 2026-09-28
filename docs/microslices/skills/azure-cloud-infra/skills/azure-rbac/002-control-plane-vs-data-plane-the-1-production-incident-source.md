---
id: skill-control-plane-vs-data-plane-the-1-production-incident-source-858cc7ef54
purpose: control plane vs data plane the 1 production incident source
source: src/vibey_tools/skills/plugins/azure-cloud-infra/skills/azure-rbac/SKILL.md
requires: ["skill-the-four-pillars-4289b75200"]
links: ["skill-scope-hierarchy-and-inheritance-fbbd4ac8ec"]
---

## Control Plane vs Data Plane — The #1 Production Incident Source

Azure operations split into two layers that NEVER cross:

**Control plane** — requests to `https://management.azure.com`. Creates, configures, and deletes Azure resources. ARM handles authorization.

**Data plane** — requests to resource-specific endpoints (`https://myaccount.blob.core.windows.net`, `https://myvault.vault.azure.net`). Uses the capabilities of a resource.

### THE CRITICAL RULE: `*` in Actions does NOT grant DataActions

Owner has `Actions: ["*"]`. Owner can fully manage a storage account but **cannot read a single blob** without an additional data plane role. This catches even experienced engineers.

| Control plane role | Data plane role | Resource |
|---|---|---|
| Storage Account Contributor | Storage Blob Data Contributor | Blob Storage |
| Key Vault Contributor | Key Vault Secrets User | Key Vault |
| Cosmos DB Contributor | Cosmos DB Built-in Data Contributor | Cosmos DB |
| Cognitive Services Contributor | Cognitive Services OpenAI User | Azure OpenAI |

**Always assign data plane roles alongside control plane roles when workloads need to access resource data.**

---
