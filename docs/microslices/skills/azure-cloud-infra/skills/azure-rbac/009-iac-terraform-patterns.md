---
id: skill-iac-terraform-patterns-1411762fb4
purpose: iac terraform patterns
source: src/vibey_tools/skills/plugins/azure-cloud-infra/skills/azure-rbac/SKILL.md
requires: ["skill-iac-bicep-patterns-for-role-assignments-c10e66a27f"]
links: ["skill-azure-cli-quick-reference-6a9569eb18"]
---

## IaC: Terraform Patterns

```hcl
resource "azurerm_role_assignment" "example" {
  scope                = data.azurerm_subscription.primary.id
  role_definition_name = "Contributor"
  principal_id         = azurerm_user_assigned_identity.example.principal_id
  principal_type       = "ServicePrincipal"
}
```

**Bulk assignments:**
```hcl
variable "role_assignments" {
  type = map(object({
    principal_id         = string
    role_definition_name = string
    scope                = string
  }))
}

resource "azurerm_role_assignment" "bulk" {
  for_each             = var.role_assignments
  scope                = each.value.scope
  role_definition_name = each.value.role_definition_name
  principal_id         = each.value.principal_id
}
```

**Custom role definition:**
```hcl
resource "azurerm_role_definition" "vm_operator" {
  name        = "vm-operator"
  scope       = data.azurerm_subscription.primary.id
  description = "Can start and restart VMs"

  permissions {
    actions     = ["*/read",
                   "Microsoft.Compute/virtualMachines/start/action",
                   "Microsoft.Compute/virtualMachines/restart/action"]
    not_actions = []
  }

  assignable_scopes = [data.azurerm_subscription.primary.id]
}
```

Use `skip_service_principal_aad_check = true` to avoid AAD replication delays. Import existing assignments with:
```bash
terraform import azurerm_role_assignment.example \
  "/subscriptions/<sub>/providers/Microsoft.Authorization/roleAssignments/<guid>"
```

---
