---
id: skill-19-crypto-agility-1bf2251582
purpose: 19 crypto agility
source: src/vibey_tools/skills/plugins/cryptography-and-encryption/skills/crypto-implementation-failures-key-management-and-agility/SKILL.md
requires: ["skill-18-key-management-e7c3b326bc"]
links: []
---

## §19. Crypto Agility

**⚠️ Every algorithm eventually weakens** — ⚠️ **MD5, SHA-1, RC4, DES, RSA-1024 were all
once fine.** **⚠️ Systems that hardcoded them are the ones in pain now, and §23.1 → `crypto-reference` is about
to repeat the lesson at unprecedented scale.**
```
⚠️ DESIGN FOR REPLACEMENT
   ⚠️ VERSION your ciphertexts and message formats from day one
   ⚠️ Negotiate algorithms rather than assuming
   ⚠️ ⚠️ Maintain a CRYPTOGRAPHIC INVENTORY — you cannot migrate
      what you cannot find, and this is the single biggest
      practical obstacle to §23.1
   ⚠️ Abstract crypto behind an interface
   ⚠️ Plan for LARGER keys and signatures (§23.1 breaks size
      assumptions in many protocols and hardware)
⚠️ THE TENSION  ⚠️ agility ADDS complexity and negotiation, which is
   itself an attack surface (downgrade attacks, §17).
   ⚠️ WireGuard deliberately chose the opposite — fixed suites,
   replace the protocol version instead. Both positions are defensible
```
