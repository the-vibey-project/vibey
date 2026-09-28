---
id: skill-2-threat-models-a9bfdedc85
purpose: 2 threat models
source: src/vibey_tools/skills/plugins/cryptography-and-encryption/skills/crypto-what-it-solves-threat-models-randomness-hashes-and-macs/SKILL.md
requires: ["skill-1-what-cryptography-does-and-doesn-t-solve-16680e86a2"]
links: ["skill-3-randomness-96ff7fb286"]
---

## §2. Threat Models

**⚠️ KERCKHOFFS'S PRINCIPLE**: ⚠️ **the system should be secure even if everything about it
except the key is public knowledge.** **⚠️ "Security through obscurity" fails because
obscurity is not a secret you can rotate.**
```
⚠️ ADVERSARY MODELS, in ascending strength
   PASSIVE / eavesdropper · ⚠️ ACTIVE / can modify, inject, replay ·
   ⚠️ CHOSEN-PLAINTEXT and CHOSEN-CIPHERTEXT · ⚠️ ADAPTIVE ·
   ⚠️ PHYSICAL ACCESS (side channels, §17) · ⚠️ INSIDER
⚠️ THE QUESTIONS THAT DEFINE A DESIGN
   ⚠️ Who is the adversary and what can they DO?
   ⚠️ What must stay secret, and FOR HOW LONG? (§23.1)
   ⚠️ What is the trusted computing base?
   ⚠️ What happens when a key is compromised? (§9, §18)
```
**⚠️ Security proofs are conditional**: ⚠️ **"provably secure" means "reduces to a problem
we believe is hard, in a stated model, assuming the implementation is correct."** **⚠️ All
three qualifiers have failed in practice.**

---

# PART I — PRIMITIVES
