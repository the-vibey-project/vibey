---
id: skill-27-quick-reference-ea0f9e658f
purpose: 27 quick reference
source: src/vibey_tools/skills/plugins/cryptography-and-encryption/skills/crypto-reference/SKILL.md
requires: ["skill-26-books-and-references-6f1311003e"]
links: ["skill-28-method-a5817d7bf5"]
---

## §27. Quick Reference

### 27.1 Picker
| Need | Answer |
|---|---|
| Encrypt data | ⚠️ **AEAD — AES-GCM or ChaCha20-Poly1305** (§7 → `crypto-symmetric-aead-public-key-and-signatures`) |
| Encrypt with a password | ⚠️ **Argon2id to derive, then AEAD** (§7 → `crypto-symmetric-aead-public-key-and-signatures`, §11 → `crypto-passwords-tls-pki-messaging-and-disk-encryption`) |
| Store passwords | ⚠️ **Argon2id, unique salt. Never a fast hash** (§11 → `crypto-passwords-tls-pki-messaging-and-disk-encryption`) |
| Verify integrity with a shared key | ⚠️ **HMAC, constant-time compare** (§5 → `crypto-what-it-solves-threat-models-randomness-hashes-and-macs`) |
| Prove authorship to third parties | ⚠️ **Ed25519 signature** (§10 → `crypto-symmetric-aead-public-key-and-signatures`) |
| Agree a key over a public channel | ⚠️ **X25519 ECDHE — ephemeral for forward secrecy** (§9 → `crypto-symmetric-aead-public-key-and-signatures`) |
| Derive several keys from one secret | ⚠️ **HKDF. Never reuse one key for two purposes** (§11 → `crypto-passwords-tls-pki-messaging-and-disk-encryption`) |
| Generate randomness | ⚠️ **OS CSPRNG** (§3 → `crypto-what-it-solves-threat-models-randomness-hashes-and-macs`) |
| Secure a web service | ⚠️ **TLS 1.3, complete chain, ACME automation** (§12 → `crypto-passwords-tls-pki-messaging-and-disk-encryption`, §23.2) |
| Store a key | ⚠️ **HSM > KMS > secrets manager. Never in source** (§18 → `crypto-implementation-failures-key-management-and-agility`) |
| Compare two secrets | ⚠️ **Constant-time comparison** (§5 → `crypto-what-it-solves-threat-models-randomness-hashes-and-macs`, §17 → `crypto-implementation-failures-key-management-and-agility`) |
| Protect data for 10+ years | ⚠️ **Plan PQC now — harvest now, decrypt later** (§23.1) |
| Pick a curve | ⚠️ **Curve25519/Ed25519 unless compliance dictates otherwise** (§8 → `crypto-symmetric-aead-public-key-and-signatures`) |

### 27.2 Design review checklist
- [ ] ⚠️ **Using a vetted library at the highest useful level** (§1 → `crypto-what-it-solves-threat-models-randomness-hashes-and-macs`)
- [ ] ⚠️ **Threat model written down — who, capabilities, secrecy duration** (§2 → `crypto-what-it-solves-threat-models-randomness-hashes-and-macs`)
- [ ] ⚠️ **All randomness from the OS CSPRNG** (§3 → `crypto-what-it-solves-threat-models-randomness-hashes-and-macs`)
- [ ] ⚠️ **AEAD everywhere; no unauthenticated ciphertext** (§7 → `crypto-symmetric-aead-public-key-and-signatures`)
- [ ] ⚠️ **Nonce uniqueness guaranteed across reboots, restores and instances** (§17 → `crypto-implementation-failures-key-management-and-agility`)
- [ ] Constant-time comparison for all secret-dependent checks (§5 → `crypto-what-it-solves-threat-models-randomness-hashes-and-macs`, §17 → `crypto-implementation-failures-key-management-and-agility`)
- [ ] ⚠️ **Passwords via Argon2id/scrypt/bcrypt, salted** (§11 → `crypto-passwords-tls-pki-messaging-and-disk-encryption`)
- [ ] Separate keys per purpose, derived via HKDF (§11 → `crypto-passwords-tls-pki-messaging-and-disk-encryption`, §18 → `crypto-implementation-failures-key-management-and-agility`)
- [ ] ⚠️ **Forward secrecy for anything transported** (§9 → `crypto-symmetric-aead-public-key-and-signatures`)
- [ ] ⚠️ **No secrets in source, env vars, logs or error messages** (§17 → `crypto-implementation-failures-key-management-and-agility`, §18 → `crypto-implementation-failures-key-management-and-agility`)
- [ ] ⚠️ **Rotation and compromise-recovery paths exist AND have been tested** (§18 → `crypto-implementation-failures-key-management-and-agility`)
- [ ] ⚠️ **Algorithms are versioned and replaceable** (§19 → `crypto-implementation-failures-key-management-and-agility`)
- [ ] ⚠️ **Cryptographic inventory exists for the PQC migration** (§19 → `crypto-implementation-failures-key-management-and-agility`, §23.1)
- [ ] ⚠️ **Certificate renewal automated via ACME** (§23.2)

---
