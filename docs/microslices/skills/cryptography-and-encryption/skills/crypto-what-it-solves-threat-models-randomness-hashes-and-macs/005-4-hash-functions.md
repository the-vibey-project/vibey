---
id: skill-4-hash-functions-9043ab7b66
purpose: 4 hash functions
source: src/vibey_tools/skills/plugins/cryptography-and-encryption/skills/crypto-what-it-solves-threat-models-randomness-hashes-and-macs/SKILL.md
requires: ["skill-3-randomness-96ff7fb286"]
links: ["skill-5-macs-68b1c6e114"]
---

## §4. Hash Functions

**⚠️ Properties**: ⚠️ **preimage resistance, second preimage resistance, and COLLISION
resistance — and collision resistance is the weakest of the three and the first to fall.**
```
⚠️ STATUS
   ⚠️ MD5  BROKEN. Collisions are trivial. ⚠️ Not for anything security-related
   ⚠️ SHA-1  BROKEN for collisions (chosen-prefix collisions demonstrated).
      ⚠️ Deprecated everywhere that matters
   ⚠️ SHA-2 (SHA-256/384/512)  ⚠️ the current workhorse. Fine
   ⚠️ SHA-3 / Keccak  different internal structure (sponge) — ⚠️ a
      structural hedge rather than a replacement
   ⚠️ BLAKE2/BLAKE3  fast, secure, good choices
⚠️ LENGTH EXTENSION  ⚠️ SHA-2 (Merkle-Damgård) is vulnerable: knowing
   H(m) lets you compute H(m ‖ padding ‖ extra) without knowing m.
   ⚠️ THIS IS WHY H(key ‖ message) IS NOT A MAC (§5)
   ⚠️ SHA-3 and BLAKE are not vulnerable
```
> **⚠️ GOTCHA — collision resistance matters when an ATTACKER CONTROLS BOTH INPUTS
> (certificates, signed documents, code signing).** ⚠️ **It matters much less for HMAC or
> for a random-input use.** **⚠️ This is why SHA-1 was catastrophic for certificates and
> merely undesirable inside HMAC — but migrate anyway, because arguing about it costs more
> than replacing it.**
**⚠️ Do NOT use general-purpose hashes for passwords** (§11 → `crypto-passwords-tls-pki-messaging-and-disk-encryption`) — ⚠️ **their speed is the
problem.**

---
