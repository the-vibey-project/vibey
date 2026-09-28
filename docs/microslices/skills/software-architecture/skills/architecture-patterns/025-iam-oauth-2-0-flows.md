---
id: skill-iam-oauth-2-0-flows-3d72903975
purpose: iam oauth 2 0 flows
source: src/vibey_tools/skills/plugins/software-architecture/skills/architecture-patterns/SKILL.md
requires: ["skill-zero-trust-f3cb1ecbee"]
links: ["skill-encryption-eb57256b0d"]
---

## IAM & OAuth 2.0 Flows

| Flow | Use When |
|---|---|
| **Authorization Code + PKCE** | Web/native apps with user interaction |
| **Client Credentials** | Machine-to-machine (M2M) |
| **Device Code** | Devices with no browser |

- **Managed Identities** (system-assigned vs user-assigned): eliminate secrets for Azure-to-Azure — always prefer over service principals for anything in Azure
- **Workload Identity Federation**: OIDC trust without secrets; use on AKS with **Workload Identity**
