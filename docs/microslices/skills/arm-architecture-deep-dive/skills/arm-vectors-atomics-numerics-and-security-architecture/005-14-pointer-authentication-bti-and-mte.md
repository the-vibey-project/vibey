---
id: skill-14-pointer-authentication-bti-and-mte-06b0de8b99
purpose: 14 pointer authentication bti and mte
source: src/vibey_tools/skills/plugins/arm-architecture-deep-dive/skills/arm-vectors-atomics-numerics-and-security-architecture/SKILL.md
requires: ["skill-13-trustzone-ffaeb2124b"]
links: ["skill-15-cca-and-realms-ad1d3faa2e"]
---

## §14. ⚠️ Pointer Authentication, BTI and MTE

> **⚠️ Three architectural mitigations for classes of memory-safety bug, and they are a good
> example of what silicon support buys over software mitigation.**
```
⚠️ ⚠️ POINTER AUTHENTICATION (PAC, ARMv8.3)
   ⚠️ ⚠️ THE INSIGHT: 64-bit pointers do not use all 64 bits.
   ⚠️ The unused top bits hold a cryptographic MAC of the
   pointer value plus a context (usually the stack pointer),
   keyed by a register the attacker cannot read
   ⚠️ PACIASP on function entry, AUTIASP on return — ⚠️ a
   corrupted return address fails authentication and faults
   ⚠️ ⚠️ THIS BREAKS ROP/JOP AT LOW COST because it needs no
   shadow stack and no extra memory
   ⚠️ LIMITS  ⚠️ signing gadget reuse, ⚠️ the MAC is short so
   brute force is conceivable in some threat models, and
   ⚠️ pointer-substitution attacks within the same context
⚠️ ⚠️ BTI (Branch Target Identification, ARMv8.5)  ⚠️ indirect
   branches may only land on a BTI landing-pad instruction —
   ⚠️ dramatically shrinking the gadget space for JOP
⚠️ ⚠️ MTE (Memory Tagging Extension, ARMv8.5)  ⚠️ THE MOST
   INTERESTING ONE
   ⚠️ 4-bit tags in pointer top bits AND in memory tag storage;
   ⚠️ the hardware checks they match on every access
   ⚠️ ⚠️ CATCHES USE-AFTER-FREE AND BUFFER OVERFLOW
   PROBABILISTICALLY (⚠️ 1-in-16 chance of a random collision)
   at low enough overhead to run in PRODUCTION, not just in
   testing — ⚠️ which is the qualitative difference from
   ASAN-style tooling
   ⚠️ SYNC mode (precise, slower) vs ASYNC (faster, imprecise)
⚠️ ⚠️ ALL THREE ARE OPTIONAL FEATURES (§4). ⚠️ Availability
   varies by silicon, and MTE deployment in particular has been
   slower than the architecture's availability
```

---
