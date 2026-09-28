---
id: skill-github-actions-oidc-federation-recommended-no-stored-secrets-f82faa6f29
purpose: github actions oidc federation recommended no stored secrets
source: src/vibey_tools/skills/plugins/azure-cloud-infra/skills/azure-rbac/SKILL.md
requires: ["skill-managed-identity-patterns-zero-credential-architecture-dea0a5c6f9"]
links: ["skill-iac-bicep-patterns-for-role-assignments-c10e66a27f"]
---

## GitHub Actions OIDC Federation (Recommended — No Stored Secrets)

GitHub Actions' built-in OIDC provider issues short-lived JWTs during workflow runs. Entra ID trusts this issuer via a federated credential.

**Setup:**

1. Create an app registration and add a federated credential:
```json
{
    "name": "GitHubActions-Production",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:my-org/my-repo:environment:Production",
    "audiences": ["api://AzureADTokenExchange"]
}
```

2. Assign RBAC roles to the service principal.

3. Configure the workflow:
```yaml
permissions:
  id-token: write
  contents: read

steps:
  - uses: azure/login@v2
    with:
      client-id: ${{ secrets.AZURE_CLIENT_ID }}
      tenant-id: ${{ secrets.AZURE_TENANT_ID }}
      subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
```

**Subject claim formats:**
- Branch: `repo:<org>/<repo>:ref:refs/heads/<branch>`
- Tag: `repo:<org>/<repo>:ref:refs/tags/<tag>`
- Environment: `repo:<org>/<repo>:environment:<name>`
- Pull request: `repo:<org>/<repo>:pull-request`

**Critical gotchas:**
- Environment names are case-sensitive
- Wildcards not supported in federated credential properties
- Maximum 20 federated credentials per application
- Audience must be `api://AzureADTokenExchange` for public cloud

**Typical role assignments for a DevOps service principal:**
| Scenario | Role | Scope |
|---|---|---|
| Deploy ARM/Bicep | Contributor | Resource group |
| Deploy ARM/Bicep with role assignments | Contributor + User Access Administrator | Resource group |
| Push to ACR | AcrPush | ACR resource |
| Deploy to AKS | AKS Cluster User + AKS RBAC Writer | AKS resource |
| Access Key Vault secrets | Key Vault Secrets User | Key Vault |
| Access blob storage data | Storage Blob Data Contributor | Storage account |

---
