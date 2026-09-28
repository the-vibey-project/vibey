---
id: skill-9-key-exchange-and-forward-secrecy-dc113217e0
purpose: 9 key exchange and forward secrecy
source: src/vibey_tools/skills/plugins/cryptography-and-encryption/skills/crypto-symmetric-aead-public-key-and-signatures/SKILL.md
requires: ["skill-8-public-key-cryptography-65e7e246a3"]
links: ["skill-10-digital-signatures-25c8913838"]
---

## §9. Key Exchange and Forward Secrecy

**⚠️ Diffie-Hellman** lets two parties derive a shared secret over a public channel —
⚠️ **and unauthenticated DH is vulnerable to machine-in-the-middle, so it must be combined
with authentication** (§10, §13 → `crypto-passwords-tls-pki-messaging-and-disk-encryption`).
> **⚠️ GOTCHA — FORWARD SECRECY is the property to insist on, and it is defined by what
> happens AFTER a compromise.** ⚠️ **With ephemeral keys (ECDHE), compromising the
> long-term private key does NOT let an attacker decrypt previously recorded sessions.**
> **⚠️ Without it — as in RSA key transport — one key compromise retroactively exposes
> everything ever recorded.**
> ⚠️ **This is exactly why "harvest now, decrypt later" is a real strategy and why §23.1 → `crypto-reference`'s
> timeline matters: recorded traffic is a stored liability.**

**⚠️ Post-compromise security / self-healing** is the complementary property — ⚠️ **the
ability to RECOVER security after a compromise, which ratcheting protocols provide** (§14 → `crypto-passwords-tls-pki-messaging-and-disk-encryption`).

---
