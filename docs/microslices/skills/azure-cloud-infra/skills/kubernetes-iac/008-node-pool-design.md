---
id: skill-node-pool-design-08e852584a
purpose: node pool design
source: src/vibey_tools/skills/plugins/azure-cloud-infra/skills/kubernetes-iac/SKILL.md
requires: ["skill-aks-security-hardening-eccb2957dc"]
links: ["skill-upgrade-strategy-6b3449855a"]
---

## Node Pool Design

Production AKS clusters must **separate system and user node pools**:

```hcl
# System node pool — only critical add-ons
resource "azurerm_kubernetes_cluster" "main" {
  default_node_pool {
    name                        = "system"
    vm_size                     = "Standard_D4s_v5"
    node_count                  = 3
    zones                       = ["1", "2", "3"]
    only_critical_addons_enabled = true  # Taint: CriticalAddonsOnly=true:NoSchedule
    os_sku                      = "AzureLinux"
  }
}

# User node pool — application workloads
resource "azurerm_kubernetes_cluster_node_pool" "user" {
  kubernetes_cluster_id = azurerm_kubernetes_cluster.main.id
  name                  = "user"
  vm_size               = "Standard_D8s_v5"
  min_count             = 3
  max_count             = 20
  enable_auto_scaling   = true
  zones                 = ["1", "2", "3"]
  os_sku                = "AzureLinux"
}
```

**Azure Linux 2.0 reaches EOL in November 2025. Migrate to AzureLinux 3 before March 2026.**

Kubenet is deprecated with removal scheduled March 2028. **Azure CNI Overlay powered by Cilium** is the recommended networking stack for new clusters — 30% reduction in service routing latency, replaces kube-proxy with eBPF, built-in network policy.

---
