---
id: skill-part-12-phase-8-infrastructure-modernization-fcc20a52d3
purpose: part 12 phase 8 infrastructure modernization
source: src/vibey_tools/skills/plugins/security-first-dev/skills/codebase-modernization/SKILL.md
requires: ["skill-part-11-phase-7-devsecops-pipeline-installation-44f0bad30e"]
links: ["skill-part-13-migration-execution-protocol-9-steps-5a5749d311"]
---

## PART 12: PHASE 8 — INFRASTRUCTURE MODERNIZATION

This phase requires coordination with the Azure admin. You produce the Bicep; the human reviews
and applies it. Do not provision infrastructure autonomously.

### 12.1 Key Vault Hardening

```bash
az keyvault show --name <vault-name> --query '{
  rbacEnabled: properties.enableRbacAuthorization,
  softDelete: properties.enableSoftDelete,
  purgeProtection: properties.enablePurgeProtection,
  publicAccess: properties.publicNetworkAccess
}'
```

```bicep
resource vault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  properties: {
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    enablePurgeProtection: true      // IRREVERSIBLE — confirm with human before applying
    publicNetworkAccess: 'Disabled'
    networkAcls: { defaultAction: 'Deny', bypass: 'AzureServices' }
  }
}
```

### 12.2 Private Endpoint — Sequence Matters

**The sequence matters.** Disabling public network access before the Private Endpoint is
configured will break all connectivity. Always:

1. Add the Private Endpoint
2. Verify connectivity via the private endpoint
3. Then disable public network access

### 12.3 Managed Identity Role Assignment — Add Before Switching Code

Always assign the Managed Identity role **before** switching the connection code:

1. Assign the role in Azure
2. Verify the assignment propagates (can take 2-5 minutes)
3. Deploy the code change
4. Remove the old connection string from Key Vault (not before)

```bicep
// Cosmos DB Built-in Data Contributor assignment
resource cosmosRoleAssignment 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-05-15' = {
  parent: cosmosAccount
  name: guid(cosmosAccount.id, apiManagedIdentityPrincipalId, 'data-contributor')
  properties: {
    roleDefinitionId: '${cosmosAccount.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002'
    principalId: apiManagedIdentityPrincipalId
    scope: cosmosAccount.id
  }
}
```

---
