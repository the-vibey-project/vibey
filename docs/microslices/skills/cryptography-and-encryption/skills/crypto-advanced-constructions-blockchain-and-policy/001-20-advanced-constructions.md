---
id: skill-20-advanced-constructions-2236bb94d5
purpose: 20 advanced constructions
source: src/vibey_tools/skills/plugins/cryptography-and-encryption/skills/crypto-advanced-constructions-blockchain-and-policy/SKILL.md
requires: []
links: ["skill-21-blockchain-cryptography-9fd0b38522"]
---

## §20. Advanced Constructions

**⚠️ Real, deployed, and frequently oversold — worth knowing what each actually gives you.**
**⚠️ ZERO-KNOWLEDGE PROOFS**: ⚠️ **prove a statement is true without revealing why.**
**zk-SNARKs (⚠️ succinct, often needing a trusted setup) and zk-STARKs (⚠️ no trusted setup,
larger proofs).** **Genuine uses in privacy and verifiable computation.**
**⚠️ MULTI-PARTY COMPUTATION**: ⚠️ **jointly compute a function over private inputs;
practical for specific problems (private set intersection, threshold operations) and still
expensive for general computation.**
**⚠️ HOMOMORPHIC ENCRYPTION**: ⚠️ **compute on ciphertext.** ⚠️ **Partially homomorphic
schemes are practical; FULLY homomorphic encryption is real, improving, and still orders of
magnitude slower than plaintext computation.** **⚠️ Treat "we use FHE" claims sceptically
and ask about the performance envelope.**
**⚠️ THRESHOLD AND SECRET SHARING**: ⚠️ **Shamir's scheme splits a secret so that k of n
shares reconstruct it — genuinely useful for root key custody.** ⚠️ **Threshold signatures
avoid ever reconstructing the key at all.**
**⚠️ Differential privacy** — ⚠️ **not cryptography, but frequently deployed alongside it;
it bounds what can be learned about any individual from aggregate release.**

---
