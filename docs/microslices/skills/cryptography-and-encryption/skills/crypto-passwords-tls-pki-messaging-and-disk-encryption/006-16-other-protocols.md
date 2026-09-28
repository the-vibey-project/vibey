---
id: skill-16-other-protocols-751ae80783
purpose: 16 other protocols
source: src/vibey_tools/skills/plugins/cryptography-and-encryption/skills/crypto-passwords-tls-pki-messaging-and-disk-encryption/SKILL.md
requires: ["skill-15-disk-and-file-encryption-5245f9a76a"]
links: []
---

## §16. Other Protocols

**⚠️ SSH**: ⚠️ **host key trust-on-first-use — ⚠️ and blindly accepting the fingerprint
defeats the whole model; prefer key-based authentication over passwords; certificate-based
SSH scales far better than distributing authorized_keys.**
**⚠️ PGP/GPG**: ⚠️ **historically important and widely criticized — no forward secrecy,
complex and error-prone UX, long-lived keys, and a web of trust that never achieved
usability.** **⚠️ For messaging, modern alternatives (§14) are better; it persists for
package and release signing where its properties fit.**
**⚠️ VPNs**: ⚠️ **WireGuard is the modern design — small, opinionated, auditable, with a
deliberately fixed cipher suite (which is the anti-agility choice, and defensible for its
purpose).** ⚠️ **Note that a commercial VPN moves trust from your ISP to the VPN operator;
it does not create anonymity.**
**⚠️ Kerberos, OAuth/OIDC, JWT** — ⚠️ **and JWT specifically has a long list of
implementation traps: the `alg: none` acceptance bug, algorithm confusion between HMAC and
RSA verification, and unverified signature paths.** **⚠️ Prefer a vetted library and
explicitly pin the expected algorithm.**

---

# PART III — WHERE IT ACTUALLY BREAKS
