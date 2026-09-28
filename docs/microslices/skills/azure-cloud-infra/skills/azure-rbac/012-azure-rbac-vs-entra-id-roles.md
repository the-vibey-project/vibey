---
id: skill-azure-rbac-vs-entra-id-roles-6beed49c87
purpose: azure rbac vs entra id roles
source: src/vibey_tools/skills/plugins/azure-cloud-infra/skills/azure-rbac/SKILL.md
requires: ["skill-common-mistakes-and-production-incidents-03b560bef1"]
links: ["skill-best-practices-f274b432f9"]
---

## Azure RBAC vs Entra ID Roles

These are completely separate systems:
- **Azure RBAC**: controls access to Azure resources (VMs, storage, networking) via the Azure Resource Manager API (`management.azure.com`)
- **Entra ID roles**: control access to directory objects (users, groups, app registrations) via Microsoft Graph API

The overlap: a Global Administrator can enable "Access management for Azure resources" to grant User Access Administrator at tenant root scope — use only for recovery scenarios.

---
