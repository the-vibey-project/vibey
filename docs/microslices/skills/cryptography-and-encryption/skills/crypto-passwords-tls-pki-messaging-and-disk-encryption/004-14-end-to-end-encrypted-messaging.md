---
id: skill-14-end-to-end-encrypted-messaging-1f39b77ae2
purpose: 14 end to end encrypted messaging
source: src/vibey_tools/skills/plugins/cryptography-and-encryption/skills/crypto-passwords-tls-pki-messaging-and-disk-encryption/SKILL.md
requires: ["skill-13-pki-and-certificates-98f42e4dfc"]
links: ["skill-15-disk-and-file-encryption-5245f9a76a"]
---

## §14. End-to-End Encrypted Messaging

**⚠️ The Signal protocol** is the reference design and is used far beyond Signal itself.
```
⚠️ X3DH  initial key agreement that works when the recipient is OFFLINE
⚠️ DOUBLE RATCHET  ⚠️ the key idea. Keys advance with every message
   ⚠️ FORWARD SECRECY — old messages stay safe if a key leaks
   ⚠️ POST-COMPROMISE SECURITY — the session HEALS after a
      compromise, once a fresh DH ratchet step occurs
⚠️ SEALED SENDER  reduces metadata exposure to the server
⚠️ THE REMAINING HARD PROBLEMS
   ⚠️ 1. KEY VERIFICATION — ⚠️ E2EE without verifying the other
      party's key only protects against the SERVER lying if you
      check. Safety numbers exist and almost nobody compares them
   ⚠️ 2. METADATA (§1) — who and when is still largely visible
   ⚠️ 3. ⚠️ ENDPOINT SECURITY — E2EE is irrelevant against a
      compromised device, and backups are frequently the weak link
   ⚠️ 4. Multi-device and group messaging complicate everything
```
**⚠️ "End-to-end encrypted" is a claim to interrogate, not accept**: ⚠️ **ask who controls
the key directory, whether backups are encrypted with a key the provider holds, and whether
the client is verifiable.**

---
