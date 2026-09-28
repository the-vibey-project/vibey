---
id: skill-secure-communications-0d8d3524c8
purpose: secure communications
source: src/vibey_tools/skills/plugins/mobile-development/skills/mobile-security/SKILL.md
requires: ["skill-secure-storage-hardware-backed-everywhere-369a4ff15c"]
links: ["skill-binary-runtime-protection-28970050c2"]
---

## Secure communications

- Enforce **TLS 1.3**.
- **OAuth 2.0 Authorization Code + PKCE** (RFC 7636) per **RFC 8252**: external browser/AppAuth
  (no embedded WebView), PKCE mandatory, **implicit flow prohibited**. **mTLS** for high-assurance
  calls. **JWT refresh-token rotation with reuse detection.**
- **Certificate pinning — pin public keys (SPKI SHA-256), not certificates, and always keep a backup
  pin:**
  - Android: OkHttp `CertificatePinner` (custom `OkHttpClientFactory` on `OkHttpClientProvider`) or
    TrustKit; plus Network Security Configuration.
  - iOS: TrustKit (`kTSKPublicKeyHashes`, requires primary + backup pin); plus ATS.
  - RN: `react-native-ssl-public-key-pinning` wraps both.
