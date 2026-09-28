---
id: skill-8-public-key-cryptography-65e7e246a3
purpose: 8 public key cryptography
source: src/vibey_tools/skills/plugins/cryptography-and-encryption/skills/crypto-symmetric-aead-public-key-and-signatures/SKILL.md
requires: ["skill-7-aead-af3e1a31c4"]
links: ["skill-9-key-exchange-and-forward-secrecy-dc113217e0"]
---

## §8. Public Key Cryptography

```
⚠️ RSA  based on factoring difficulty
   ⚠️ Use ≥2048-bit, preferably 3072+. ⚠️ RSA-1024 is not adequate
   ⚠️ PADDING IS MANDATORY AND SPECIFIC: OAEP for encryption,
      PSS for signatures. ⚠️ "Textbook RSA" (no padding) is
      completely insecure, and PKCS#1 v1.5 encryption padding has
      a long history of oracle attacks (Bleichenbacher, and it
      keeps coming back)
⚠️ ELLIPTIC CURVE  ⚠️ much smaller keys for equivalent strength —
   ~256-bit EC ≈ ~3072-bit RSA
   ⚠️ Curve25519/X25519 and Ed25519 are the modern defaults —
      designed to be MISUSE-RESISTANT, which matters more than
      marginal performance
   ⚠️ NIST P-curves are widely deployed and required in some
      compliance contexts; ⚠️ they are harder to implement safely
      (point validation, invalid curve attacks)
⚠️ ASYMMETRIC CRYPTO IS SLOW  ⚠️ so it is used to establish or wrap
   a SYMMETRIC key, not to encrypt bulk data. This is hybrid
   encryption and it is what essentially every real system does
```

---
