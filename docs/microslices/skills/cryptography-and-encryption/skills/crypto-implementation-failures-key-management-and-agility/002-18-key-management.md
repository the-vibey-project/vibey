---
id: skill-18-key-management-e7c3b326bc
purpose: 18 key management
source: src/vibey_tools/skills/plugins/cryptography-and-encryption/skills/crypto-implementation-failures-key-management-and-agility/SKILL.md
requires: ["skill-17-implementation-failure-modes-437bbf838d"]
links: ["skill-19-crypto-agility-1bf2251582"]
---

## §18. ⚠️ Key Management

> **⚠️ The hard part, and the part that gets least attention in tutorials.**
```
⚠️ THE LIFECYCLE  generate (§3) → distribute → store → use →
   rotate → revoke → destroy. ⚠️ Every stage has failure modes
⚠️ STORAGE, best to worst
   ⚠️ HSM or secure element (⚠️ key never leaves the hardware)
   ⚠️ Cloud KMS / platform keystore
   ⚠️ Secrets manager with access control and audit
   ⚠️ Environment variables (⚠️ leak into logs, crash dumps and
      child processes)
   ⚠️ HARDCODED IN SOURCE — ⚠️ and therefore in git history forever.
      ⚠️ Still one of the most common real-world findings
⚠️ PRINCIPLES
   ⚠️ SEPARATE KEYS FOR SEPARATE PURPOSES — derive with HKDF (§11)
   ⚠️ Least privilege on key access; audit every use
   ⚠️ ⚠️ PLAN FOR COMPROMISE. Rotation is not a formality —
      it is the thing you'll need under pressure
   ⚠️ Key escrow and recovery are a genuine trade-off: losing the
      key means losing the data, and escrow creates a target
   ⚠️ ⚠️ Test the recovery path. An untested restore is not a backup
```
**⚠️ Secret scanning in CI and git history** is high-value and cheap. ⚠️ **Assume anything
committed once is permanently public and rotate it rather than deleting the commit.**

---
