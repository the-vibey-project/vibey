---
id: skill-core-principle-separation-of-concerns-19153397de
purpose: core principle separation of concerns
source: src/vibey_tools/skills/plugins/azure-cloud-infra/skills/kubernetes-iac/SKILL.md
requires: []
links: ["skill-gitops-the-operational-model-b0bab2a443"]
---

## Core Principle: Separation of Concerns

**Platform IaC** (Terraform/Bicep for AKS cluster, VNet, ACR, Key Vault) and **Application IaC** (Helm/Kustomize for workload manifests) operate on completely different lifecycles, use different tools, require different credentials, and must live in **separate repositories with separate pipelines**.

| Dimension | Platform IaC | Application IaC |
|---|---|---|
| Changes | Infrequently (cluster upgrades, networking) | Daily (app deployments) |
| Blast radius | High — can destroy the cluster | Namespace-scoped |
| Credentials | Cloud-provider credentials (Terraform/Bicep) | Cluster credentials only |
| Owner | Platform team | Application teams |
| Tools | Terraform, Bicep | Helm, Kustomize |

**Never mix platform and app resources in one Terraform state.** An application change must never be able to accidentally destroy the cluster.

---
