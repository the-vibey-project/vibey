---
id: skill-managed-identity-patterns-zero-credential-architecture-dea0a5c6f9
purpose: managed identity patterns zero credential architecture
source: src/vibey_tools/skills/plugins/azure-cloud-infra/skills/azure-rbac/SKILL.md
requires: ["skill-role-definition-structure-c18b99e499"]
links: ["skill-github-actions-oidc-federation-recommended-no-stored-secrets-f82faa6f29"]
---

## Managed Identity Patterns — Zero-Credential Architecture

Managed identities eliminate all credentials from Azure workload configurations.

**System-assigned**: tied to resource lifecycle; deleted when resource is deleted. Use when permissions should follow the resource.

**User-assigned**: pre-created, shareable across multiple resources, survives resource deletion. Preferred for production — create with role assignments before cluster provisioning.

```bash
# Create user-assigned managed identity
az identity create --name myapp-identity --resource-group myRG

# Assign a role to it
az role assignment create \
  --assignee-object-id "$(az identity show --name myapp-identity --resource-group myRG --query principalId -o tsv)" \
  --assignee-principal-type ServicePrincipal \
  --role "Storage Blob Data Contributor" \
  --scope "/subscriptions/<sub>/resourceGroups/myRG/providers/Microsoft.Storage/storageAccounts/myStorage"
```

**For AKS workloads** — use Workload Identity (replaces deprecated Pod Identity, EOL September 2025):
1. Enable OIDC issuer and Workload Identity on the cluster
2. Create a user-assigned managed identity with role assignments
3. Create a Kubernetes service account annotated with `azure.workload.identity/client-id`
4. Create a federated identity credential linking the managed identity to the service account
5. Label pods with `azure.workload.identity/use: "true"`

---
