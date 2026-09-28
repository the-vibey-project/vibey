---
id: skill-mfa-on-mobile-4e034a03dd
purpose: mfa on mobile
source: src/vibey_tools/skills/plugins/mobile-development/skills/mobile-security/SKILL.md
requires: ["skill-privacy-2ffbfa73d8"]
links: []
---

## MFA on mobile

- **FIDO2/WebAuthn platform authenticators & passkeys** (phishing-resistant, bound to the RP ID;
  private key never leaves the device):
  - iOS: `AuthenticationServices` + AASA associated domains + iCloud Keychain sync.
  - Android: **Credential Manager API** (unified passkeys/passwords/federated; third-party providers
    on Android 14+) + Digital Asset Links.
- **TOTP** (RFC 6238); push MFA via **Microsoft Authenticator with number matching**; **SMS OTP is
  discouraged** (SIM-swap/SS7; NIST SP 800-63B restricts it).
- **Entra ID MFA** via MSAL + **Conditional Access**; **Entra External ID (B2C)** flows for RN;
  **step-up auth** for high-risk operations (MASVS-AUTH "additional authentication"); OAuth **Device
  Authorization Grant** (RFC 8628) for constrained devices.
- **Silent SSO via the MSAL broker** — Authenticator holds the **PRT** in Secure Enclave /
  hardware-backed Keystore (iOS uses URL-scheme IPC; Android uses the broker within the Work Profile).
  Multi-account support via Intune multi-identity.
