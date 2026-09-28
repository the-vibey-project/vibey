---
id: skill-iac-bicep-vs-terraform-ad7efc1807
purpose: iac bicep vs terraform
source: src/vibey_tools/skills/plugins/azure-cloud-infra/skills/azure-services-catalog/SKILL.md
requires: ["skill-cost-optimization-35c90c4630"]
links: ["skill-identity-zero-trust-85a9a15185"]
---

## IaC: Bicep vs Terraform

**Consensus:** both are production-ready; standardize on one for new projects.

| | Bicep | Terraform |
|---|---|---|
| Best for | Azure-only teams | Multi-cloud or heavy third-party integration |
| State file | No | Yes (management overhead) |
| Azure day-0 support | Yes | Delayed (provider maturity) |
| Provider ecosystem | Azure-only | Mature, broad |
| CI/CD | Azure CLI native | State management required |

Migration between them is rarely worth it — standardize on one and let old projects attrit.

---
