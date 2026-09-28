---
id: skill-21-blockchain-cryptography-9fd0b38522
purpose: 21 blockchain cryptography
source: src/vibey_tools/skills/plugins/cryptography-and-encryption/skills/crypto-advanced-constructions-blockchain-and-policy/SKILL.md
requires: ["skill-20-advanced-constructions-2236bb94d5"]
links: ["skill-22-law-and-policy-dc576c9e89"]
---

## §21. Blockchain Cryptography

**⚠️ What it actually uses**: ⚠️ **hash functions for linking and proof-of-work, Merkle
trees for efficient inclusion proofs, ECDSA or Schnorr signatures for transaction
authorization.** **⚠️ The cryptography is standard; the novelty is the consensus mechanism
and the incentive design, not the primitives.**
**⚠️ Merkle trees** are independently useful — ⚠️ **certificate transparency (§13 → `crypto-passwords-tls-pki-messaging-and-disk-encryption`), git,
and file integrity systems all use them.**
> **⚠️ GOTCHA — "blockchain" is not a cryptographic property.** ⚠️ **It does not make data
> true, only tamper-evident once recorded, and it says nothing about whether the input was
> correct.** **⚠️ And "your keys, your coins" means key management (§18 → `crypto-implementation-failures-key-management-and-agility`) with no recovery
> path — which has resulted in permanent, irreversible loss at large scale.**

---
