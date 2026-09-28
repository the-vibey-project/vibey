---
id: skill-10-digital-signatures-25c8913838
purpose: 10 digital signatures
source: src/vibey_tools/skills/plugins/cryptography-and-encryption/skills/crypto-symmetric-aead-public-key-and-signatures/SKILL.md
requires: ["skill-9-key-exchange-and-forward-secrecy-dc113217e0"]
links: []
---

## §10. Digital Signatures

**⚠️ Sign with the PRIVATE key, verify with the PUBLIC key** — ⚠️ **the inverse of
encryption, and the confusion is common.**
```
⚠️ ALGORITHMS  ⚠️ Ed25519 (fast, deterministic, misuse-resistant —
   the modern default) · ECDSA (widely deployed) · RSA-PSS
⚠️ ECDSA'S NONCE HAZARD  ⚠️ ECDSA requires a per-signature random
   value k. ⚠️ REUSING k ACROSS TWO SIGNATURES REVEALS THE PRIVATE
   KEY through simple algebra. ⚠️ This has broken real systems,
   including a well-known games console. ⚠️ Even BIASED k leaks
   the key over many signatures
   ⚠️ Deterministic nonce generation (RFC 6979) or Ed25519 removes
   this entire class of failure
⚠️ SIGN THE RIGHT THING  ⚠️ sign a hash of a canonical encoding;
   ⚠️ ambiguity in what was signed is a real attack surface
⚠️ DOMAIN SEPARATION  ⚠️ include context so a signature valid in one
   protocol cannot be replayed as valid in another
```
