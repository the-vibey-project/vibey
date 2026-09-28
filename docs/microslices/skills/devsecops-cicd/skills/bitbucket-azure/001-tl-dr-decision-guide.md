---
id: skill-tl-dr-decision-guide-02c53ea61c
purpose: tl dr decision guide
source: src/vibey_tools/skills/plugins/devsecops-cicd/skills/bitbucket-azure/SKILL.md
requires: []
links: ["skill-the-critical-azure-oidc-gap-e299adaabb"]
---

## TL;DR Decision Guide

**Use Bitbucket Pipelines if:**
- Already committed to the Atlassian/Jira ecosystem
- Azure surface is App Service, AKS, ACR, Static Web Apps
- Acceptable to mitigate the OIDC-to-Azure gap with per-environment service-principal secrets + auto-rotation

**Switch to GitHub Actions or Azure DevOps if:**
- Security posture requires federated identity end-to-end with zero stored secrets
- Need hosted Windows or macOS runners (Bitbucket has Linux-only hosted runners)
- Release pipelines require multi-stage, multi-approver gates with auditable approvals
- DevSecOps requires first-party SCA/secret scanning/SBOM (GitHub Advanced Security)

---
