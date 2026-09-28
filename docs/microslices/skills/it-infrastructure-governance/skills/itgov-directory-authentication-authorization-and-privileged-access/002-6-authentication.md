---
id: skill-6-authentication-80e428ff60
purpose: 6 authentication
source: src/vibey_tools/skills/plugins/it-infrastructure-governance/skills/itgov-directory-authentication-authorization-and-privileged-access/SKILL.md
requires: ["skill-5-directory-services-and-hybrid-identity-93641f1401"]
links: ["skill-7-authorization-rbac-and-beyond-c96b8d6948"]
---

## §6. Authentication

```
SOMETHING YOU KNOW    password  ⚠️ the weakest factor
SOMETHING YOU HAVE    token, key, device
SOMETHING YOU ARE     biometric
```
**⚠️ Not all MFA is equal, and this is the practical point:**
```
SMS / VOICE      ⚠️ WEAKEST — SIM swap, and real-time phishing relay
TOTP / OATH      ⚠️ better, but still phishable — a user can be tricked into
                 entering the code on a fake login page
PUSH             ⚠️ MFA fatigue attacks; number matching mitigates
PHISHING-RESISTANT  ⚠️ FIDO2/WebAuthn, passkeys, platform authenticators,
                 certificate-based — the credential is CRYPTOGRAPHICALLY BOUND to
                 the origin, so a relay attack cannot work
```
**⚠️ The mechanism is what matters**: **phishing-resistant methods bind the credential to
the legitimate site's origin, so an attacker-in-the-middle proxy gets nothing usable.**
**Every other method can be relayed in real time by a phishing kit, and modern kits do
exactly this routinely.**

**SSO** (SAML, OIDC/OAuth 2.0), **conditional/risk-based access** (⚠️ **evaluating device
compliance, location, sign-in risk and application sensitivity at each authentication —
this is the policy engine that makes identity a real perimeter**), **session management
and token lifetime**, **break-glass accounts** (⚠️ **excluded from policy, hardware-key
protected, monitored, and tested — an untested break-glass account is a bet you haven't
verified**).
**⚠️ Certificates and PKI**: **CA hierarchy, expiry (⚠️ a leading cause of self-inflicted
outages), revocation, and internal CA protection as a Tier 0 asset.**

---
