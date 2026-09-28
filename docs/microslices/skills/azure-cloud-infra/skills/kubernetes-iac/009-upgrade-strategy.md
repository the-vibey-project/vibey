---
id: skill-upgrade-strategy-6b3449855a
purpose: upgrade strategy
source: src/vibey_tools/skills/plugins/azure-cloud-infra/skills/kubernetes-iac/SKILL.md
requires: ["skill-node-pool-design-08e852584a"]
links: ["skill-environment-promotion-pattern-176e8946c7"]
---

## Upgrade Strategy

Use both cluster auto-upgrade and node OS auto-upgrade with separate maintenance windows:

```hcl
resource "azurerm_kubernetes_cluster" "main" {
  automatic_upgrade_channel  = "stable"  # Auto-upgrade to latest patch of N-1 minor version
  node_os_upgrade_channel    = "NodeImage"

  maintenance_window_auto_upgrade {
    frequency   = "Weekly"
    interval    = 1
    duration    = 4
    day_of_week = "Sunday"
    start_time  = "02:00"
    utc_offset  = "+00:00"
  }

  maintenance_window_node_os {
    frequency   = "Weekly"
    interval    = 1
    duration    = 4
    day_of_week = "Wednesday"
    start_time  = "02:00"
    utc_offset  = "+00:00"
  }
}
```

Configure surge upgrades on node pools (`max_surge = "33%"`) to provision extra nodes during rolling upgrades. Always define PodDisruptionBudgets — misconfigured PDBs block the entire upgrade process.

---
