---
id: skill-service-retirements-act-now-9f7d89fd95
purpose: service retirements act now
source: src/vibey_tools/skills/plugins/azure-cloud-infra/skills/azure-services-catalog/SKILL.md
requires: ["skill-identity-zero-trust-85a9a15185"]
links: ["skill-production-staging-roadmap-a102c1539d"]
---

## Service Retirements — Act Now

| Service | Status | Action Required |
|---|---|---|
| **Log Analytics agent (MMA)** | Retired November 2024 | Migrate to Azure Monitor Agent (AMA) with Data Collection Rules |
| **Azure AD B2C** | No new sales May 1, 2025; P2 discontinues March 15, 2026; support "until at least May 2030" | Migrate to **Microsoft Entra External ID** (GA Sept 2024); plan 3–9 months for migration |
| **AzureAD/MSOnline PowerShell** | Deprecated March 2024, retiring through 2025 | Migrate to Microsoft Graph PowerShell; Azure AD Graph API blocked for new apps |
| **Prompt Flow** | Retires April 20, 2027 | Migrate to Microsoft Agent Framework |

**Entra External ID migration note:** B2C custom policies don't port directly; Entra External ID still has gaps (OTP-only MFA, tenant-level branding) — validate feature parity before committing.

---
