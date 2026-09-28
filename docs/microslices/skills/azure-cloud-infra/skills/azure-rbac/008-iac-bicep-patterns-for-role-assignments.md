---
id: skill-iac-bicep-patterns-for-role-assignments-c10e66a27f
purpose: iac bicep patterns for role assignments
source: src/vibey_tools/skills/plugins/azure-cloud-infra/skills/azure-rbac/SKILL.md
requires: ["skill-github-actions-oidc-federation-recommended-no-stored-secrets-f82faa6f29"]
links: ["skill-iac-terraform-patterns-1411762fb4"]
---

## IaC: Bicep Patterns for Role Assignments

**API version:** `2022-04-01`

```bicep
// Basic role assignment
resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, principalId, roleDefinitionId)
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'   // ALWAYS specify this
  }
}
```

**Resource-level scoping:**
```bicep
resource blobRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: storageAccount
  name: guid(storageAccount.id, principalId, blobContributorRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}
```

**CRITICAL Bicep rules:**
- `name` must be a deterministic GUID using `guid()` with stable seeds (scope ID + principal ID + role definition ID) for idempotency
- Always specify `principalType` — omitting it causes intermittent failures with service principals and managed identities
- Deploying role assignments requires `Microsoft.Authorization/roleAssignments/write` — Contributor alone is NOT sufficient. Use Owner or User Access Administrator.

**Reusable module** (`modules/roleAssignment.bicep`):
```bicep
param principalId string
param roleDefinitionId string
@allowed(['User','Group','ServicePrincipal','ForeignGroup','Device'])
param principalType string = 'ServicePrincipal'

resource role 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(subscription().id, resourceGroup().id, principalId, roleDefinitionId)
  properties: {
    principalId: principalId
    principalType: principalType
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', roleDefinitionId)
  }
}
```

---
