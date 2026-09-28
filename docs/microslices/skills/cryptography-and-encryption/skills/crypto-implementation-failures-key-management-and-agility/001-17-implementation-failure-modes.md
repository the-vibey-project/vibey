---
id: skill-17-implementation-failure-modes-437bbf838d
purpose: 17 implementation failure modes
source: src/vibey_tools/skills/plugins/cryptography-and-encryption/skills/crypto-implementation-failures-key-management-and-agility/SKILL.md
requires: []
links: ["skill-18-key-management-e7c3b326bc"]
---

## §17. ⚠️ Implementation Failure Modes

> **⚠️ This is where cryptography fails in the real world. The maths holds; the code
> doesn't.**
```
⚠️ NONCE / IV REUSE  ⚠️ THE most catastrophic and most common
   ⚠️ In CTR/GCM, reusing a (key, nonce) pair XORs two plaintexts
      together and, in GCM, ⚠️ can reveal the authentication key,
      allowing forgery
   ⚠️ Counters that reset on reboot, VM restore, or across
      instances are the usual cause. ⚠️ Use random 96+-bit nonces
      or a construction that tolerates misuse (AES-GCM-SIV)
⚠️ TIMING SIDE CHANNELS  ⚠️ comparison, table lookups, branches on
   secret data. ⚠️ Use constant-time comparison; ⚠️ note the
   compiler may optimize your careful code away
⚠️ PADDING ORACLES  ⚠️ distinguishing "bad padding" from "bad MAC"
   in an error message or timing lets an attacker decrypt.
   ⚠️ AEAD (§7) removes the class
⚠️ POWER/EM/ACOUSTIC side channels — physical access
⚠️ FAULT INJECTION  ⚠️ inducing an error during RSA-CRT signing
   can leak the private key from ONE faulty signature
⚠️ ERROR MESSAGES  ⚠️ any distinguishable failure is an oracle
⚠️ MEMORY  ⚠️ keys in swap, core dumps, logs, or freed-but-not-zeroed
   buffers. ⚠️ Garbage-collected languages make zeroization hard
⚠️ DOWNGRADE / VERSION NEGOTIATION  ⚠️ an attacker forcing the
   weakest mutually supported option. ⚠️ Remove weak options
⚠️ SPECULATIVE EXECUTION  Spectre/Meltdown-class leakage
```
**⚠️ The pattern worth internalizing**: ⚠️ **almost all of these are about the system
leaking information through a channel the mathematical model didn't include.**

---
