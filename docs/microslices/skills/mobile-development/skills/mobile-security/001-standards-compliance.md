---
id: skill-standards-compliance-5df1938753
purpose: standards compliance
source: src/vibey_tools/skills/plugins/mobile-development/skills/mobile-security/SKILL.md
requires: []
links: ["skill-secure-storage-hardware-backed-everywhere-369a4ff15c"]
---

## Standards & compliance

- **MASVS v2.1.0** (released Jan 18, 2024) adds **MASVS-PRIVACY**; eight control groups (24
  requirements): **STORAGE, CRYPTO, AUTH, NETWORK, PLATFORM, CODE, RESILIENCE, PRIVACY**, verified via
  **MASTG**. From v2.0.0 the standard "does not contain verification levels … replaced by **MAS Testing
  Profiles**" — so RFP language asking for "MASVS Level 2" is stale framing.
- **Mobile Top 10 2024** (first major revision since 2016): **M1 Improper Credential Usage** (now #1 —
  hardcoded API keys/secrets in APKs/IPAs), M2 Inadequate Supply Chain Security, M3 Insecure
  Authentication/Authorization, M4 Insufficient Input/Output Validation, M5 Insecure Communication,
  M6 Inadequate Privacy Controls, M7 Insufficient Binary Protections, M8 Security Misconfiguration,
  M9 Insecure Data Storage, M10 Insufficient Cryptography.
