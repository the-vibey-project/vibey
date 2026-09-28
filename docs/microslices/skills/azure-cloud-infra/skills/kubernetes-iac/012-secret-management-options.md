---
id: skill-secret-management-options-334c62ddae
purpose: secret management options
source: src/vibey_tools/skills/plugins/azure-cloud-infra/skills/kubernetes-iac/SKILL.md
requires: ["skill-production-workload-checklist-0c887abb40"]
links: []
---

## Secret Management Options

Three approaches for different needs:

1. **External Secrets Operator (ESO)** — recommended for GitOps. Synchronizes secrets from Azure Key Vault into Kubernetes Secrets via ExternalSecret CRDs safe to commit to Git. Authenticate to Key Vault using Workload Identity.

2. **Azure Key Vault CSI Driver** — mounts secrets directly as CSI volumes (secrets never stored in etcd). Ideal when avoiding Kubernetes Secrets entirely. Enable with `enable_key_vault_secrets_provider = true` in Terraform.

3. **SOPS with Azure Key Vault** — encrypts secret values while keeping keys readable. Perfect for GitOps diffs. Native Flux support. Keys are readable in Git; only values are encrypted.

Never store unencrypted secrets in Git. Four defense layers: pre-commit hooks with gitleaks, CI gitleaks scanning, SOPS encryption, ExternalSecret CRDs as the primary pattern.
