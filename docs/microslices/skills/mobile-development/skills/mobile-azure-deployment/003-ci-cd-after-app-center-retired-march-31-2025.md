---
id: skill-ci-cd-after-app-center-retired-march-31-2025-49e257290b
purpose: ci cd after app center retired march 31 2025
source: src/vibey_tools/skills/plugins/mobile-development/skills/mobile-azure-deployment/SKILL.md
requires: ["skill-backend-data-tier-d767de03b8"]
links: ["skill-observability-tie-in-32be950088"]
---

## CI/CD after App Center (retired March 31, 2025)

App Center was retired except for Analytics & Diagnostics (support extended, initially to
June 30, 2026, then to end of March 2027 pending the Azure Monitor mobile migration — **confirm the
live date**). Replacements:

- **Builds:** Azure DevOps Pipelines (macOS agents for iOS, signing certs in **Azure Key Vault**)
  and/or GitHub Actions + **Fastlane** (`match` signing, `gym` build, `deliver`/`supply` store
  uploads, `snapshot`/`screengrab` screenshots). Bitrise/Codemagic are mobile-first alternatives.
- **OTA:** **EAS Build/Update** for Expo; **CodePush** continues standalone — both with version /
  mandatory-update enforcement.
- **Distribution:** TestFlight + App Store Connect API; Google Play Internal Testing; Intune LOB;
  Firebase App Distribution.
- **Bundle optimization:** Hermes bytecode, R8/ProGuard, **AAB over APK**. Semantic versioning + build
  numbering. Manage iOS distribution/enterprise certs and Android keystores in Key Vault.
