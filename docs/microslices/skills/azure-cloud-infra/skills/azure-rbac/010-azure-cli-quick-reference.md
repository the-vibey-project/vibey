---
id: skill-azure-cli-quick-reference-6a9569eb18
purpose: azure cli quick reference
source: src/vibey_tools/skills/plugins/azure-cloud-infra/skills/azure-rbac/SKILL.md
requires: ["skill-iac-terraform-patterns-1411762fb4"]
links: ["skill-common-mistakes-and-production-incidents-03b560bef1"]
---

## Azure CLI Quick Reference

```bash
# Create assignment using object ID (faster — bypasses Graph query)
az role assignment create \
  --assignee-object-id "<objectId>" \
  --assignee-principal-type "ServicePrincipal" \
  --role "Storage Blob Data Contributor" \
  --scope "/subscriptions/<sub>/resourceGroups/<rg>"

# List assignments for a specific principal
az role assignment list --assignee "<principalId>" --scope "<scope>"

# List all Owner assignments on a subscription
az role assignment list --role "Owner" --scope "/subscriptions/<sub>"

# Find action strings for a provider
az provider operation show --namespace Microsoft.Storage
az provider operation show --namespace Microsoft.Compute

# Create custom role from JSON file
az role definition create --role-definition @vm-operator.json
```

---
