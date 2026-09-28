---
id: skill-3-randomness-96ff7fb286
purpose: 3 randomness
source: src/vibey_tools/skills/plugins/cryptography-and-encryption/skills/crypto-what-it-solves-threat-models-randomness-hashes-and-macs/SKILL.md
requires: ["skill-2-threat-models-a9bfdedc85"]
links: ["skill-4-hash-functions-9043ab7b66"]
---

## §3. ⚠️ Randomness

> **⚠️ The most under-appreciated failure point, and it breaks everything above it
> silently. Bad randomness produces output that LOOKS fine.**
```
⚠️ USE THE OPERATING SYSTEM CSPRNG. Always.
   ⚠️ /dev/urandom, getrandom(), BCryptGenRandom, SecRandomCopyBytes
   ⚠️ NEVER a language's default rand()/Math.random() — those are
      statistical PRNGs, deliberately fast and entirely predictable
⚠️ WHERE IT HAS GONE WRONG IN REALITY
   ⚠️ Insufficient entropy at BOOT on embedded devices and VMs —
      ⚠️ producing duplicate keys across many devices
   ⚠️ VM cloning replaying the same RNG state
   ⚠️ A distribution patch that reduced the effective keyspace
      of every key generated for years
   ⚠️ Deterministic nonce generation from a predictable counter (§17)
⚠️ THE /dev/random vs /dev/urandom DEBATE IS SETTLED on modern
   systems: ⚠️ once seeded, urandom is fine and blocking is not a
   security benefit
```

---
