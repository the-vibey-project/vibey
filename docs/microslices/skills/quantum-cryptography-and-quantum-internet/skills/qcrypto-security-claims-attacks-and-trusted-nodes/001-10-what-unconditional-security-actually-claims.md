---
id: skill-10-what-unconditional-security-actually-claims-5c9fe833b3
purpose: 10 what unconditional security actually claims
source: src/vibey_tools/skills/plugins/quantum-cryptography-and-quantum-internet/skills/qcrypto-security-claims-attacks-and-trusted-nodes/SKILL.md
requires: []
links: ["skill-11-attacks-on-real-qkd-systems-644c7ac985"]
---

## §10. ⚠️ What "Unconditional Security" Actually Claims

> **⚠️ The most oversold phrase in the field. It has a precise technical meaning that is
> much narrower than the marketing implies.**
```
⚠️ WHAT IT MEANS  ⚠️ security does not depend on assumptions about
   the ADVERSARY'S COMPUTATIONAL POWER. That's genuinely different
   from classical crypto and it is a real result
⚠️ WHAT IT STILL ASSUMES — and every one of these has failed somewhere
   ⚠️ The devices behave as the model says (§11 — they don't)
   ⚠️ The labs are secure and not leaking side channels
   ⚠️ ⚠️ THE CLASSICAL CHANNEL IS AUTHENTICATED
   ⚠️ The random number generators are sound
   ⚠️ Quantum mechanics is correct (fine) and the specific
      model of the source and detector is accurate (often not)
```
> **⚠️ GOTCHA — THE AUTHENTICATION BOOTSTRAP IS THE STRUCTURAL PROBLEM, and it is why
> agencies object** (§20 → `qcrypto-official-position-qrng-quantum-threat-and-choosing`). ⚠️ **QKD cannot authenticate. Without authentication, an
> attacker simply runs a machine-in-the-middle: separate QKD sessions with each party, and
> the physics detects nothing because each link is genuinely undisturbed.**
> **⚠️ So QKD requires either (a) classical public-key authentication — reintroducing
> exactly the classical dependency it was meant to remove — or (b) a PRE-SHARED SYMMETRIC
> KEY.**
> ⚠️ **And if you already have a pre-shared symmetric key, you could have used it directly
> with a symmetric algorithm. ⚠️ QKD's honest claim is that it EXPANDS a small pre-shared
> key into a large one, which is a real service and a much more modest one than "unhackable
> communication."**

---
