---
id: skill-identity-zero-trust-85a9a15185
purpose: identity zero trust
source: src/vibey_tools/skills/plugins/azure-cloud-infra/skills/azure-services-catalog/SKILL.md
requires: ["skill-iac-bicep-vs-terraform-ad7efc1807"]
links: ["skill-service-retirements-act-now-9f7d89fd95"]
---

## Identity & Zero Trust

- **Managed Identities:** always preferred over service principals for Azure-to-Azure auth — no secret management, no credential rotation
- **Zero Trust stack:** Entra ID + Conditional Access + PIM (just-in-time role activation) + Defender for Cloud
- Use **Azure RBAC built-in roles** at the narrowest scope — avoid Owner/Contributor at subscription/management-group scope
- **Key Vault references:** let App Service/Functions/AKS consume secrets without storing them in config
- Distinguish **Azure RBAC** (resource-plane) from **Entra ID roles** (directory/tenant-plane)

---
