---
id: skill-part-13-infrastructure-security-and-devsecops-a83108d32e
purpose: part 13 infrastructure security and devsecops
source: src/vibey_tools/skills/plugins/security-first-dev/skills/security-first-scrum/SKILL.md
requires: ["skill-part-12-data-layer-security-984d1a5813"]
links: ["skill-part-14-ai-self-governance-89f0b0cc43"]
---

## PART 13: INFRASTRUCTURE SECURITY AND DEVSECOPS

### Azure Key Vault — Required Bicep Configuration

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

### Private Endpoints

All PaaS services use Private Endpoints. Required DNS zones:
- Key Vault: `privatelink.vaultcore.azure.net`
- Cosmos DB: `privatelink.documents.azure.com`
- PostgreSQL: `privatelink.postgres.database.azure.com`
- Databricks: `privatelink.azuredatabricks.net`
- Storage: `privatelink.blob.core.windows.net`

Known Bicep bug: `environment().suffixes.keyvaultDns` returns `.vault.azure.net` but the correct
private DNS zone is `privatelink.vaultcore.azure.net` — always hardcode.

### DevSecOps Pipeline — All Gates Required

```yaml
name: Security-First Scrum CI/CD
jobs:
  sast-semgrep:       # p/security-audit p/owasp-top-ten p/csharp p/typescript
  sast-codeql:        # csharp, javascript
  sca-snyk:           # --severity-threshold=high
  secrets-scan:       # gitleaks, full history (fetch-depth: 0)
  container-scan:     # trivy CRITICAL,HIGH exit-code 1
  iac-scan:           # checkov bicep soft_fail false
  build-and-test:     # dotnet test with coverage gate

  deploy:
    needs: [sast-semgrep, sast-codeql, sca-snyk, secrets-scan, container-scan, iac-scan, build-and-test]
    if: github.ref == 'refs/heads/main'
```

**The pipeline is a security control. Never bypass, soft-fail, or comment out gates to hit a
deadline. If a gate blocks, fix the finding.**

### AKS Pod Security (Workload Identity — Pod Identity is EOL September 2025)

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
