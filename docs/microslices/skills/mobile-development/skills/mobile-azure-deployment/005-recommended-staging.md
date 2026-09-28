---
id: skill-recommended-staging-1f9166e358
purpose: recommended staging
source: src/vibey_tools/skills/plugins/mobile-development/skills/mobile-azure-deployment/SKILL.md
requires: ["skill-observability-tie-in-32be950088"]
links: []
---

## Recommended staging

1. **Foundation (wk 0–4):** RN New Architecture (or native), Entra ID + MSAL broker auth, decommission
   App Center, move CI/CD to Azure DevOps/GitHub Actions + Fastlane (certs in Key Vault).
2. **Secure backend & data (wk 4–10):** APIM → Container Apps/AKS → Cosmos DB with Private Endpoints;
   Easy Auth + JWT validation at APIM; offline-first persistence with change-feed sync + explicit
   conflict strategy; public-key cert pinning with a backup pin.
3. **Hardening & distribution (wk 10–16):** Intune App Protection Policies + Conditional Access
   (MAM-WE for BYOD); Play Integrity / App Attest; passkeys/FIDO2 + step-up auth; Sentry + App Insights;
   distribute via Intune LOB / TestFlight / Play Internal Testing.
