---
id: skill-secure-storage-hardware-backed-everywhere-369a4ff15c
purpose: secure storage hardware backed everywhere
source: src/vibey_tools/skills/plugins/mobile-development/skills/mobile-security/SKILL.md
requires: ["skill-standards-compliance-5df1938753"]
links: ["skill-secure-communications-0d8d3524c8"]
---

## Secure storage (hardware-backed everywhere)

- **iOS:** Keychain accessibility — use `kSecAttrAccessibleWhenUnlockedThisDeviceOnly` for
  non-syncable secrets; `.biometryCurrentSet` invalidates keys on biometric-enrollment change;
  **Secure Enclave** for non-exportable private keys; `NSFileProtection` for files.
- **Android:** Keystore **TEE** vs **StrongBox** (API 28+, dedicated SE) with **key attestation**;
  verify `isInsideSecureHardware()`.
- **Both:** SQLCipher; biometric-bound keys via `LAContext` (iOS) / `BiometricPrompt.CryptoObject`
  (Android).
- **Root/jailbreak detection + attestation:** **Play Integrity API** (replaced SafetyNet) on Android;
  **App Attest / DeviceCheck** on iOS.
