---
id: skill-11-password-storage-and-kdfs-d663c948e2
purpose: 11 password storage and kdfs
source: src/vibey_tools/skills/plugins/cryptography-and-encryption/skills/crypto-passwords-tls-pki-messaging-and-disk-encryption/SKILL.md
requires: []
links: ["skill-12-tls-c7dfa7b3e8"]
---

## §11. ⚠️ Password Storage and KDFs

> **⚠️ Passwords need a fundamentally different treatment from everything else here,
> because they are LOW ENTROPY. The design goal is to make guessing expensive.**
```
⚠️ USE A PASSWORD HASHING FUNCTION, NOT A HASH
   ⚠️ Argon2id — the current recommendation
   ⚠️ scrypt · bcrypt (⚠️ note its input length limit) · PBKDF2
      (⚠️ acceptable where required for compliance, weakest of these)
⚠️ WHY  ⚠️ these are deliberately SLOW and MEMORY-HARD.
   ⚠️ Memory hardness specifically resists GPU and ASIC attack,
   which is where the economics of cracking live
⚠️ SALT  ⚠️ unique per user, stored alongside. Defeats rainbow
   tables and stops identical passwords hashing identically
⚠️ PEPPER  a secret held separately from the database — ⚠️ useful
   defence in depth against database-only compromise
⚠️ NEVER  ⚠️ MD5, SHA-256 or any fast hash, salted or not.
   ⚠️ A GPU does billions of SHA-256 per second
⚠️ KDFs FOR KEY DERIVATION (different job)  ⚠️ HKDF for deriving
   multiple keys from one high-entropy secret. ⚠️ Do not reuse a
   single key for multiple purposes — derive separate ones
```
**⚠️ The modern guidance on password POLICY has inverted**: ⚠️ **length over composition
rules, no forced periodic rotation without evidence of compromise, and screening against
known-breached password lists.**

---

# PART II — PROTOCOLS
