---
id: skill-6-symmetric-encryption-e53319d970
purpose: 6 symmetric encryption
source: src/vibey_tools/skills/plugins/cryptography-and-encryption/skills/crypto-symmetric-aead-public-key-and-signatures/SKILL.md
requires: []
links: ["skill-7-aead-af3e1a31c4"]
---

## §6. Symmetric Encryption

**⚠️ AES is the standard** (128/192/256-bit keys), ⚠️ **with hardware acceleration
essentially universal.** **⚠️ ChaCha20 is the good software-only alternative and is faster
without AES instructions.**
```
⚠️ MODES OF OPERATION — where block ciphers actually get used
   ⚠️ ECB  ⚠️ NEVER. Identical plaintext blocks produce identical
      ciphertext blocks — the famous encrypted-penguin image is
      still visible. ⚠️ ECB leaks structure
   ⚠️ CBC  needs a RANDOM, UNPREDICTABLE IV, and ⚠️ needs padding,
      which creates PADDING ORACLE exposure (§17)
   ⚠️ CTR  turns a block cipher into a stream cipher.
      ⚠️ NEVER REUSE A (key, nonce) PAIR — see §17
   ⚠️ GCM / ChaCha20-Poly1305  ⚠️ AEAD. Use these (§7)
⚠️ KEY SIZE  ⚠️ AES-128 remains secure against classical attack;
   AES-256 is the conservative choice and is already
   quantum-adequate (§23.1)
```
**⚠️ Stream ciphers**: ⚠️ **RC4 is broken and must not be used.** **⚠️ The general stream
cipher hazard is keystream reuse, which is catastrophic and easy to do accidentally.**

---
