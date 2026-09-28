---
id: skill-role-definition-structure-c18b99e499
purpose: role definition structure
source: src/vibey_tools/skills/plugins/azure-cloud-infra/skills/azure-rbac/SKILL.md
requires: ["skill-built-in-role-catalog-key-roles-1b7de826d2"]
links: ["skill-managed-identity-patterns-zero-credential-architecture-dea0a5c6f9"]
---

## Role Definition Structure

```json
{
  "Name": "VM Operator",
  "IsCustom": true,
  "Description": "Can monitor, start, restart, and stop VMs. Cannot create or delete.",
  "Actions": [
    "*/read",
    "Microsoft.Compute/virtualMachines/start/action",
    "Microsoft.Compute/virtualMachines/restart/action",
    "Microsoft.Compute/virtualMachines/deallocate/action"
  ],
  "NotActions": [],
  "DataActions": [],
  "NotDataActions": [],
  "AssignableScopes": [
    "/subscriptions/<subscription-id>"
  ]
}
```

Action strings: `{Company}.{ProviderName}/{resourceType}/{action}`. Wildcards supported. `NotActions` is NOT a deny — it subtracts from wildcards but can be overridden by another role assignment.

Custom role limits:
- 5,000 per Entra tenant
- `AssignableScopes` cannot use root (`/`) — only built-in roles
- Only one management group allowed in `AssignableScopes`
- Custom roles with `DataActions` cannot be assigned at management group scope

---
