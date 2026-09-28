---
id: skill-1-what-cryptography-does-and-doesn-t-solve-16680e86a2
purpose: 1 what cryptography does and doesn t solve
source: src/vibey_tools/skills/plugins/cryptography-and-encryption/skills/crypto-what-it-solves-threat-models-randomness-hashes-and-macs/SKILL.md
requires: ["skill-0-routing-c67f7db199"]
links: ["skill-2-threat-models-a9bfdedc85"]
---

## §1. ⚠️ What Cryptography Does and Doesn't Solve

```
⚠️ THE FOUR GOALS
   ⚠️ CONFIDENTIALITY  nobody else can read it
   ⚠️ INTEGRITY  it hasn't been altered
   ⚠️ AUTHENTICITY  it's from who you think
   ⚠️ NON-REPUDIATION  they can't later deny sending it
   ⚠️ These are DIFFERENT and require DIFFERENT mechanisms.
   ⚠️ Confusing them is the root of many design errors
⚠️ WHAT CRYPTO CANNOT DO
   ⚠️ Protect against a compromised ENDPOINT. ⚠️ If the attacker is
      on the device, encryption in transit is irrelevant
   ⚠️ Hide METADATA — ⚠️ who talked to whom, when, how often and how
      much. ⚠️ Metadata is frequently more revealing than content
   ⚠️ Fix a bad trust model. ⚠️ Encryption to the wrong party is
      perfectly secure and completely useless
   ⚠️ Solve authorization, availability, or insider abuse
   ⚠️ Compensate for users who will click through any warning
```
> **⚠️ GOTCHA — "don't roll your own crypto" is often misunderstood as being about
> ALGORITHMS. It's mostly about PROTOCOLS AND IMPLEMENTATIONS.** ⚠️ **Nobody sensible
> designs a new block cipher; plenty of teams compose existing primitives into a novel
> protocol, and that is where the failures come from.**
> **⚠️ The practical version: use libsodium/NaCl, Tink, the platform's crypto API, or an
> equivalent — at the highest level that solves your problem. ⚠️ If your code contains a
> mode of operation, an IV, or a padding decision, you are already lower-level than you
> probably need to be.**

---
