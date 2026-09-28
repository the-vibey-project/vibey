---
id: skill-bicep-azure-native-alternative-c0f0d41e6d
purpose: bicep azure native alternative
source: src/vibey_tools/skills/plugins/azure-cloud-infra/skills/kubernetes-iac/SKILL.md
requires: ["skill-terraform-for-aks-provisioning-20b00e2bbb"]
links: ["skill-aks-security-hardening-eccb2957dc"]
---

## Bicep: Azure-Native Alternative

Bicep requires **no state management** — Azure Resource Manager tracks state directly. Eliminates an entire category of operational concerns (state locking, corruption, storage). Day-zero support for new Azure features.

**When to choose Bicep:** Azure-only teams wanting the simplest experience, teams without Terraform investment.

**When to choose Terraform:** Multi-cloud environments, non-Azure resources (Datadog, GitHub, DNS providers), or teams with existing Terraform investment.

```bicep
param location string = resourceGroup().location
param clusterName string

resource aks 'Microsoft.ContainerService/managedClusters@2024-02-01' = {
  name: clusterName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${aksIdentity.id}': {}
    }
  }
  properties: {
    agentPoolProfiles: [
      {
        name: 'system'
        count: 3
        vmSize: 'Standard_D4s_v5'
        mode: 'System'
        osType: 'Linux'
        availabilityZones: ['1', '2', '3']
        enableAutoScaling: true
        minCount: 3
        maxCount: 9
        nodeTaints: ['CriticalAddonsOnly=true:NoSchedule']
      }
    ]
    networkProfile: {
      networkPlugin: 'azure'
      networkPluginMode: 'overlay'
      networkDataplane: 'cilium'
    }
    oidcIssuerProfile: { enabled: true }
    securityProfile: { workloadIdentity: { enabled: true } }
    enableRBAC: true
    aadProfile: {
      managed: true
      enableAzureRBAC: true
    }
  }
}
```

Use `az deployment group what-if` for plan-equivalent previews before applying.

---
