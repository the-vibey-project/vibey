---
id: skill-25-numbers-b90dd5f1d6
purpose: 25 numbers
source: src/vibey_tools/skills/plugins/cryptography-and-encryption/skills/crypto-reference/SKILL.md
requires: ["skill-24-misconceptions-317781149b"]
links: ["skill-26-books-and-references-6f1311003e"]
---

## §25. Numbers

```
⚠️ AES  128/192/256 · ⚠️ AES-256 already quantum-adequate
⚠️ RSA  ⚠️ ≥2048, prefer 3072+ · ⚠️ EC ~256-bit ≈ RSA ~3072-bit
⚠️ Broken hashes  ⚠️ MD5 (collisions trivial) · SHA-1 (chosen-prefix)
⚠️ Nonce  ⚠️ NEVER reuse (key, nonce). GCM: 96-bit standard
⚠️ Password hashing  ⚠️ Argon2id preferred · never a fast hash
⚠️ ML-KEM (FIPS 203)  ⚠️ pubkeys ~800–1568 B · ciphertexts ~768–1568 B
⚠️ ML-DSA (FIPS 204)  ⚠️ signatures ~2420–4595 B
⚠️ SLH-DSA (FIPS 205)  ⚠️ signatures ~7856–49856 B
⚠️ PQC security levels  L1≈AES-128 · L3≈AES-192 · L5≈AES-256
⚠️ NIST IR 8547  ⚠️ RSA-2048/ECC-256 deprecated 2030, disallowed 2035
⚠️ NSA CNSA 2.0  ⚠️ ML-KEM-1024, ML-DSA-87; NSS migration by 2030–2035
⚠️ TLS hybrid KEX  ⚠️ X25519MLKEM768
⚠️ Cert lifetimes  ⚠️ 398 → 200 (Mar 2026) → 100 (Mar 2027) → 47 (Mar 2029)
⚠️ DCV reuse  ⚠️ 398 → 200 → ... → 10 days (2029), ~35 revalidations/yr
⚠️ SC-081v3 vote  ⚠️ 29 for, 0 against, 5 abstentions (11 Apr 2025)
```

---
