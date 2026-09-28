---
id: skill-24-misconceptions-317781149b
purpose: 24 misconceptions
source: src/vibey_tools/skills/plugins/cryptography-and-encryption/skills/crypto-reference/SKILL.md
requires: ["skill-23-what-s-live-checked-august-2026-a719c82920"]
links: ["skill-25-numbers-b90dd5f1d6"]
---

## §24. Misconceptions

| Misconception | Correction |
|---|---|
| Encryption makes data secure | ⚠️ **It solves four specific problems and not others** (§1 → `crypto-what-it-solves-threat-models-randomness-hashes-and-macs`) |
| Encrypted means private | ⚠️ **Metadata is often more revealing than content** (§1 → `crypto-what-it-solves-threat-models-randomness-hashes-and-macs`) |
| Don't roll your own crypto means algorithms | ⚠️ **Mostly protocols and implementations** (§1 → `crypto-what-it-solves-threat-models-randomness-hashes-and-macs`) |
| Secret algorithms are safer | ⚠️ **Kerckhoffs. You can't rotate obscurity** (§2 → `crypto-what-it-solves-threat-models-randomness-hashes-and-macs`) |
| Any random number will do | ⚠️ **OS CSPRNG only. rand() is predictable** (§3 → `crypto-what-it-solves-threat-models-randomness-hashes-and-macs`) |
| SHA-256 of a password is fine | ⚠️ **Its speed is the problem. Use Argon2id** (§4 → `crypto-what-it-solves-threat-models-randomness-hashes-and-macs`, §11 → `crypto-passwords-tls-pki-messaging-and-disk-encryption`) |
| HMAC is just hashing the key with the message | ⚠️ **H(key‖msg) breaks via length extension** (§4 → `crypto-what-it-solves-threat-models-randomness-hashes-and-macs`, §5 → `crypto-what-it-solves-threat-models-randomness-hashes-and-macs`) |
| A MAC is a signature | ⚠️ **Shared key — no non-repudiation** (§5 → `crypto-what-it-solves-threat-models-randomness-hashes-and-macs`) |
| ECB is fine for small data | ⚠️ **It leaks structure. Never** (§6 → `crypto-symmetric-aead-public-key-and-signatures`) |
| Encryption alone protects the message | ⚠️ **Unauthenticated ciphertext is malleable. Use AEAD** (§7 → `crypto-symmetric-aead-public-key-and-signatures`) |
| MAC-then-encrypt is fine | ⚠️ **Encrypt-then-MAC — or just use AEAD** (§7 → `crypto-symmetric-aead-public-key-and-signatures`) |
| RSA without padding still works | ⚠️ **Textbook RSA is insecure. OAEP/PSS** (§8 → `crypto-symmetric-aead-public-key-and-signatures`) |
| Bigger RSA keys are always better | ⚠️ **EC gives equivalent strength far smaller** (§8 → `crypto-symmetric-aead-public-key-and-signatures`) |
| TLS means forward secrecy | ⚠️ **Only with ephemeral key exchange** (§9 → `crypto-symmetric-aead-public-key-and-signatures`) |
| Reusing a signature nonce is sloppy | ⚠️ **It reveals the private key outright** (§10 → `crypto-symmetric-aead-public-key-and-signatures`) |
| Salting is enough for passwords | ⚠️ **Salt defeats rainbow tables, not GPUs** (§11 → `crypto-passwords-tls-pki-messaging-and-disk-encryption`) |
| Force password rotation every 90 days | ⚠️ **Modern guidance inverted this** (§11 → `crypto-passwords-tls-pki-messaging-and-disk-encryption`) |
| A valid certificate means you're safe | ⚠️ **Any of hundreds of CAs can issue for any domain** (§13 → `crypto-passwords-tls-pki-messaging-and-disk-encryption`) |
| Revocation works | ⚠️ **Browsers frequently fail open** (§13 → `crypto-passwords-tls-pki-messaging-and-disk-encryption`, §23.2) |
| E2EE protects me completely | ⚠️ **Not against a compromised endpoint, or unverified keys** (§14 → `crypto-passwords-tls-pki-messaging-and-disk-encryption`) |
| Full disk encryption protects a running machine | ⚠️ **It protects data at rest** (§15 → `crypto-passwords-tls-pki-messaging-and-disk-encryption`) |
| Nonce reuse is a minor bug | ⚠️ **Catastrophic — can reveal the auth key in GCM** (§17 → `crypto-implementation-failures-key-management-and-agility`) |
| Timing differences are too small to exploit | ⚠️ **They're a demonstrated attack class** (§17 → `crypto-implementation-failures-key-management-and-agility`) |
| Environment variables are secure storage | ⚠️ **They leak into logs and dumps** (§18 → `crypto-implementation-failures-key-management-and-agility`) |
| Deleting the commit removes the secret | ⚠️ **Rotate it. It's public** (§18 → `crypto-implementation-failures-key-management-and-agility`) |
| Blockchain makes data true | ⚠️ **Tamper-evident once recorded. Not correct** (§21 → `crypto-advanced-constructions-blockchain-and-policy`) |
| Quantum computers break AES | ⚠️ **AES-256 is already adequate. It's public-key that breaks** (§23.1) |
| No quantum computer, so no urgency | ⚠️ **Harvest now, decrypt later** (§23.1) |
| PQC algorithms are proven safe | ⚠️ **SIKE and Rainbow broke during evaluation. Hence hybrids** (§23.1) |
| I can keep buying 1-year certificates | ⚠️ **200 days now, 47 by 2029** (§23.2) |

---
