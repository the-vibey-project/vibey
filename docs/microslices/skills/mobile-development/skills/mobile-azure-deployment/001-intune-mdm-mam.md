---
id: skill-intune-mdm-mam-3fa4205cc1
purpose: intune mdm mam
source: src/vibey_tools/skills/plugins/mobile-development/skills/mobile-azure-deployment/SKILL.md
requires: []
links: ["skill-backend-data-tier-d767de03b8"]
---

## Intune / MDM & MAM

- **MDM** = full device management; **MAM** = app-level management.
- **MAM-WE (without enrollment)** protects corporate data on unmanaged **BYOD** via App Protection
  Policies (PIN, encryption, copy/paste/save-as restrictions, **selective wipe checked every 30 min**).
  Must be paired with **Conditional Access requiring an app-protection policy**.
- App Config Policies push settings; on enrolled iOS, `IntuneMAMUPN`/`IntuneMAMOID`/`IntuneMAMDeviceID`
  auto-flow to managed apps. Data-protection framework has three levels (Enterprise basic/L1 → high).
- Apps become managed via the **Intune App SDK** or App Wrapping Tool — the SDK team officially
  supports **native Android/iOS/.NET/MAUI, NOT React Native** (RN integration is unsupported,
  at-your-own-risk; validate with Microsoft).
- Enrollment: **Apple Business Manager (ABM)**, **Android Enterprise** (Work Profile/COPE/COBO).
  Defender for Endpoint and Play Integrity / hardware attestation feed compliance → Entra ID →
  Conditional Access. Distribute LOB `.ipa`/`.apk`/`.aab` as line-of-business apps.
