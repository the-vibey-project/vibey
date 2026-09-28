---
id: skill-domain-6-azure-infrastructure-and-devsecops-c998879c2a
purpose: domain 6 azure infrastructure and devsecops
source: src/vibey_tools/skills/plugins/security-first-dev/skills/cybersecurity-implementation/SKILL.md
requires: ["skill-domain-5-ai-tool-security-claude-code-and-cursor-96de2a1c8a"]
links: ["skill-twelve-highest-impact-actions-in-priority-order-87444ea524"]
---

## DOMAIN 6: AZURE INFRASTRUCTURE AND DEVSECOPS

### Foundational — Key Vault, Private Endpoints, Network Isolation

**Azure Key Vault — required Bicep configuration:**
```bicep
resource vault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: 'kv-${uniqueString(resourceGroup().id)}'
  location: location
  properties: {
    sku: { family: 'A', name: 'premium' }
    tenantId: tenant().tenantId
    enableRbacAuthorization: true       // Use RBAC, not legacy access policies
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    enablePurgeProtection: true         // Cannot be disabled once set — intentional
    publicNetworkAccess: 'Disabled'
    networkAcls: { defaultAction: 'Deny', bypass: 'AzureServices' }
  }
}
```

**Private Endpoints for Key Vault:**
```bicep
resource kvPrivateEndpoint 'Microsoft.Network/privateEndpoints@2023-05-01' = {
  name: 'pe-keyvault'
  location: location
  properties: {
    subnet: { id: dataSubnetId }
    privateLinkServiceConnections: [{
      name: 'kv-connection'
      properties: {
        privateLinkServiceId: vault.id
        groupIds: ['vault']
      }
    }]
  }
}
```

**Required private DNS zones (always hardcode — never use suffixes expressions):**
- Key Vault: `privatelink.vaultcore.azure.net`
- Cosmos DB: `privatelink.documents.azure.com`
- PostgreSQL: `privatelink.postgres.database.azure.com`
- Databricks: `privatelink.azuredatabricks.net`
- Storage: `privatelink.blob.core.windows.net`

**Known Bicep bug:** `environment().suffixes.keyvaultDns` returns `.vault.azure.net` but the
correct private DNS zone is `privatelink.vaultcore.azure.net` — always hardcode.

**Note on Azure Blueprints:** Blueprints is deprecated (EOL July 2026). Replace with Deployment
Stacks: `az stack group create --name stack-myapp --deny-settings-mode denyWriteAndDelete`

### Intermediate — Defender for Cloud, KQL Detection Queries, App Insights

**Enable all Microsoft Defender for Cloud plans:**
```bash
az security pricing create --name CloudPosture --tier Standard
az security pricing create --name VirtualMachines --tier Standard
az security pricing create --name AppService --tier Standard
az security pricing create --name KeyVaults --tier Standard
az security pricing create --name CosmosDbs --tier Standard
az security pricing create --name Containers --tier Standard
az security pricing create --name Arm --tier Standard
```

**Application Insights — use connection string, not instrumentation key (deprecated):**
```bicep
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'ai-webapi'
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalyticsWorkspace.id
    DisableLocalAuth: true  // Force Managed Identity, not local auth keys
  }
}
```

**KQL detection queries for Log Analytics:**

```kql
// Brute force detection — more than 10 failed logins per hour per user/IP
SigninLogs
| where ResultType != "0"
| summarize FailedCount = count() by UserPrincipalName, IPAddress, bin(TimeGenerated, 1h)
| where FailedCount > 10

// Key Vault access anomalies — unauthorized or forbidden access attempts
AzureDiagnostics
| where ResourceProvider == "MICROSOFT.KEYVAULT"
| where ResultSignature in ("Forbidden", "Unauthorized")
| summarize Count = count() by CallerIPAddress, OperationName

// Sensitive role assignments — detect privilege escalation attempts
AzureActivity
| where OperationNameValue =~ "MICROSOFT.AUTHORIZATION/ROLEASSIGNMENTS/WRITE"
| project TimeGenerated, Caller, OperationNameValue, ResourceGroup

// API rate limit violations
AppRequests
| where ResultCode == "429"
| summarize Count = count() by ClientIP, bin(TimeGenerated, 5m)
| where Count > 50
```

### Advanced — Full DevSecOps Pipeline, Managed Identity Chain, AKS Workload Identity

**Complete DevSecOps pipeline — all gates required, no soft-fails:**
```yaml
# .github/workflows/devsecops.yml
name: DevSecOps Pipeline
on:
  push: { branches: [main] }
  pull_request: { branches: [main] }
permissions:
  security-events: write
  contents: read

jobs:
  sast-semgrep:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: returntocorp/semgrep-action@v1
        with:
          config: 'p/security-audit p/owasp-top-ten p/csharp p/typescript'
          generateSarif: true
      - uses: github/codeql-action/upload-sarif@v3
        with: { sarif_file: semgrep.sarif }
        if: always()

  sast-codeql:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: github/codeql-action/init@v3
        with: { languages: 'csharp, javascript' }
      - uses: github/codeql-action/analyze@v3

  sca-snyk:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: snyk/actions/dotnet@master
        env: { SNYK_TOKEN: '${{ secrets.SNYK_TOKEN }}' }
        with: { args: '--severity-threshold=high' }

  secrets-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }  # full history required
      - uses: gitleaks/gitleaks-action@v2
        env: { GITHUB_TOKEN: '${{ secrets.GITHUB_TOKEN }}' }

  container-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t myapp:${{ github.sha }} .
      - uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'myapp:${{ github.sha }}'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'

  iac-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: bridgecrewio/checkov-action@master
        with: { directory: 'infra/', framework: bicep, soft_fail: false }

  deploy:
    needs: [sast-semgrep, sast-codeql, sca-snyk, secrets-scan, container-scan, iac-scan]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: production
    steps:
      - run: echo "All security gates passed — deploying"
```

**Zero-secrets Managed Identity chain — full Bicep:**
```bicep
// User-assigned identity shared across services
resource appIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'id-myapp'
  location: location
}

// Key Vault Secrets User (role ID: 4633458b-17de-408a-b874-0445c86b69e6)
resource kvRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: vault
  name: guid(vault.id, appIdentity.id, '4633458b-17de-408a-b874-0445c86b69e6')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions',
      '4633458b-17de-408a-b874-0445c86b69e6')
    principalId: appIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// Cosmos DB Built-in Data Contributor
resource cosmosRole 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-05-15' = {
  parent: cosmosAccount
  name: guid(cosmosAccount.id, appIdentity.properties.principalId, 'contributor')
  properties: {
    roleDefinitionId: '${cosmosAccount.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002'
    principalId: appIdentity.properties.principalId
    scope: cosmosAccount.id
  }
}

// Storage Blob Data Contributor (role ID: ba92f5b4-2d11-453d-a403-e96b0029c9fe)
resource storageRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: storageAccount
  name: guid(storageAccount.id, appIdentity.id, 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions',
      'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
    principalId: appIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}
```

**AKS Workload Identity** (Pod Identity is deprecated, EOL September 2025):

```yaml
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    seccompProfile: { type: RuntimeDefault }
  containers:
  - name: api
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities: { drop: [ALL] }
```

---
