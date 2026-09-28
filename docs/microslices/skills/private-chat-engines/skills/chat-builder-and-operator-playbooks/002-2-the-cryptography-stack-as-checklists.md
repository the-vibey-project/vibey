---
id: skill-2-the-cryptography-stack-as-checklists-ae51596a6c
purpose: 2 the cryptography stack as checklists
source: src/vibey_tools/skills/plugins/private-chat-engines/skills/chat-builder-and-operator-playbooks/SKILL.md
requires: ["skill-1-choose-the-protocol-shape-before-touching-crypto-de285f9273"]
links: ["skill-2-5-the-server-you-have-to-write-anyway-fundamentals-stable-20c7089dc8"]
---

## 2. The cryptography stack, as checklists

**Session establishment**
- ☑ Hybrid (classical + PQ) establishment TODAY if you start now — PQXDH (X25519+ML-KEM-1024) is
  the template; harvest-now-decrypt-later is real.
- ☑ One-time pre-key economics: sizing upload cadence vs. exhaustion is a real ops parameter
  (Signal's "last-resort" ML-KEM pre-key pattern is the graceful answer).
- ☑ Auth story: identity keys + fingerprints/safety numbers at minimum; **transparency** (key
  transparency like WhatsApp's auto-verify or Apple's CKV) if you serve billions.

**Ongoing ratchet**
- ☑ DH ratchet for PCS; symmetric chains for FS; bounded skipped-key caches (`MAX_SKIP`) as a
  storage-DoS defence — enforced in the [OMEMO 2 library](https://github.com/conversejs/libomemo.js/releases/tag/v2.0.0)
  for exactly this reason.
- ☑ PQ inside the ratchet, not beside it: Signal's SPQR (ML-KEM-768, erasure-coded 42-byte chunk
  drip) and SimpleX's double-KEM sntrup761 augmentation are the two working designs; choose one
  pattern; do not invent a third.
- ☑ Downgrade discipline: Signal's pattern — unknown-extension tolerance, downgrade only in a
  session's first messages, MAC-protected; then an enforce flag once the fleet converges. Copy it.

**Multi-device**
- ☑ Per-device sessions fanout (Sesame pattern) with client-side membership management; or MLS
  native multi-member model. Never share long-lived identity private keys between devices —
  backup/recovery via sealed storage (4S-style recovery key; SVR-style enclave KDF for
  PIN-recoverable profile keys only if you can staff HSM/enclave engineering — see §5).

**The boring baseline (get these wrong and the ratchet does not save you)**
- ☑ **TLS 1.3** on every client↔server and server↔server hop; never disable certificate verification.
- ☑ **HKDF** for key derivation; **Argon2id** for any password hashing (memory-hard, resists
  GPU/ASIC); **Ed25519** for identity signatures and **X25519** for key exchange.
- ☑ **The OS CSPRNG for all randomness — never a language's default `rand()`.**

> **⚠️ DO NOT IMPLEMENT CRYPTOGRAPHY YOURSELF**
> Use vetted libraries at the highest level of abstraction that solves the problem. **If your code
> contains a mode of operation, an IV, or a padding decision, you are already lower-level than you
> probably need to be.** The primitives are rarely broken; the systems built from them fail
> constantly — implementation bugs, key-management errors, protocol-composition mistakes.

**Key custody — the algorithm choice is easy; where the keys live is where systems fail**
- ☑ **Identity keys**: generated on-device, private half never leaves it, only the public half is
  published. Platform secure storage only — Keychain (iOS), Keystore (Android), libsecret (Linux) —
  **never** the app's sandbox files.
- ☑ **One-time pre-keys**: generated in batches on-device and uploaded; the server dispenses one at
  a time and deletes it after use; the client re-uploads when the pool runs low.
- ☑ **Signed pre-keys**: rotate every few days to weeks; retain the *previous* private key briefly
  for messages already in flight, then delete it.
- ☑ **Session/ratchet state** (chain keys, DH key pair, message counters): never leaves the session;
  persisted encrypted at rest under a key derived from the device passcode, or the next app restart
  loses the conversation.

**Client message pipeline**
- ☑ **Fail closed on the client**: when AEAD verification fails, alert the user and display *nothing*.
  A decryption failure is a possible key-substitution or tampering event, not a rendering bug — and
  "show it anyway with a warning icon" is how that signal gets trained out of users. On send, a
  direction change means the DH ratchet step happens *before* the message key is derived; on both
  paths, persist ratchet state after every message or the next app restart loses the session.

**Before you ship**
- ☑ External security audit by a firm with cryptography *and* messaging experience — not a generic
  application pentest shop.
- ☑ Fuzz the cryptographic code paths.
- ☑ Test **key substitution**: what does the client do when the server returns a different identity
  key? (This is the attack safety numbers and key transparency exist for — prove your client
  notices.)
- ☑ Test **device migration**: does the old device lose access when it should?
- ☑ Test **group membership changes**: can a departed member read new messages? Can a new member
  read old ones? Both are policy decisions — make them deliberately, then test the answer you chose.
- ☑ Test **dropped, reordered and replayed** messages, then **corrupted ciphertext**: authentication
  must fail closed, visibly, and without rendering anything.
- ☑ Penetration-test the server, and re-read the threat model against **what you built** rather than
  what you designed.
