---
id: skill-15-disk-and-file-encryption-5245f9a76a
purpose: 15 disk and file encryption
source: src/vibey_tools/skills/plugins/cryptography-and-encryption/skills/crypto-passwords-tls-pki-messaging-and-disk-encryption/SKILL.md
requires: ["skill-14-end-to-end-encrypted-messaging-1f39b77ae2"]
links: ["skill-16-other-protocols-751ae80783"]
---

## §15. Disk and File Encryption

**⚠️ Full disk encryption** (BitLocker, FileVault, LUKS, dm-crypt) ⚠️ **protects data AT
REST — meaning a powered-off, lost or stolen device.** **⚠️ It provides essentially nothing
against malware on a running, unlocked system, which is the misconception that matters.**
**⚠️ Key hierarchy**: ⚠️ **a volume key wrapped by a key derived from the user's password
(§11) and/or sealed to a TPM/Secure Enclave — which is what makes hardware-bound
protections and rate limiting possible.**
**⚠️ Threat-model caveats**: ⚠️ **cold boot attacks against keys in RAM, DMA attacks,
evil-maid attacks against unencrypted boot components (⚠️ Secure Boot addresses part of
this), and the fact that "encrypted at rest" in cloud storage usually means the PROVIDER
holds the keys.**
**⚠️ Deniable encryption and hidden volumes** — ⚠️ **the cryptography works and the threat
model usually doesn't, because their existence is often inferable and legal compulsion
doesn't require proof.**

---
