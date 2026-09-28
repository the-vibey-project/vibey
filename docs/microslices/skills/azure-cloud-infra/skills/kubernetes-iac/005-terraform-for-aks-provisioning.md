---
id: skill-terraform-for-aks-provisioning-20b00e2bbb
purpose: terraform for aks provisioning
source: src/vibey_tools/skills/plugins/azure-cloud-infra/skills/kubernetes-iac/SKILL.md
requires: ["skill-kustomize-overlays-and-patches-5480ec6daa"]
links: ["skill-bicep-azure-native-alternative-c0f0d41e6d"]
---

## Terraform for AKS Provisioning

### Module Structure (Preferred Over Workspaces)

**Directory-based separation is preferred over workspaces for production** — workspaces create risk of applying to the wrong environment.

```
infrastructure/
├── modules/
│   ├── vnet/           # VNet, subnets, NSGs
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── aks/            # AKS cluster, node pools
│   ├── acr/            # Azure Container Registry
│   ├── keyvault/       # Key Vault + RBAC
│   └── monitoring/     # Log Analytics, Managed Prometheus
└── environments/
    ├── dev/
    │   └── main.tf     # composes modules with dev values
    ├── staging/
    └── prod/
```

Each environment root module composes the modules with different variable values. Bridge environments via Terraform outputs consumed by application configuration.

### Remote State in Azure Blob Storage

```hcl
terraform {
  backend "azurerm" {
    resource_group_name  = "rg-terraform-state"
    storage_account_name = "stterraformstate"
    container_name       = "tfstate"
    key                  = "prod/aks.tfstate"
  }
}
```

Azure Blob Storage natively supports state locking via blob leases — no extra configuration needed. Enable blob versioning for rollback. One state file per environment prevents cross-environment blast radius.

### OIDC Authentication for CI/CD (No Stored Secrets)

```hcl
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "=4.14.0"    # Pin exactly; commit .terraform.lock.hcl
    }
  }
}

provider "azurerm" {
  features {}
  use_oidc = true  # Uses OIDC federated credentials from GitHub Actions
}
```

### AKS Cluster Module Example

```hcl
module "aks" {
  source = "../../modules/aks"

  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  cluster_name        = "aks-${var.environment}"

  # System node pool
  system_node_count  = 3
  system_vm_size     = "Standard_D4s_v5"
  availability_zones = ["1", "2", "3"]

  # Networking — Azure CNI Overlay with Cilium (recommended for new clusters)
  vnet_subnet_id     = module.vnet.aks_subnet_id
  network_plugin     = "azure"
  network_plugin_mode = "overlay"
  network_dataplane  = "cilium"

  # Identity — user-assigned for pre-provisioned role assignments
  identity_type      = "UserAssigned"
  user_assigned_identity_id = azurerm_user_assigned_identity.aks.id

  # Security
  enable_oidc_issuer       = true
  enable_workload_identity = true
  azure_rbac_enabled       = true   # Azure RBAC for Kubernetes authorization
  private_cluster_enabled  = true

  # Add-ons
  enable_azure_policy = true
  enable_key_vault_secrets_provider = true
  enable_monitor       = true
}
```

### Azure Verified Modules

The **Azure Verified Modules** (`Azure/avm-ptn-aks-production/azurerm`, released October 2024) provide enterprise-grade, Microsoft-supported AKS provisioning. Use as the starting point for production clusters.

```hcl
module "aks_production" {
  source  = "Azure/avm-ptn-aks-production/azurerm"
  version = "~> 0.1"

  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  name                = "aks-prod"
}
```

---
