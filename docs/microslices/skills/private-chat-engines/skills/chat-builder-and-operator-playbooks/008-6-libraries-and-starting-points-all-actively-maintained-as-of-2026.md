---
id: skill-6-libraries-and-starting-points-all-actively-maintained-as-of-2026-c6f821b674
purpose: 6 libraries and starting points all actively maintained as of 2026
source: src/vibey_tools/skills/plugins/private-chat-engines/skills/chat-builder-and-operator-playbooks/SKILL.md
requires: ["skill-5-5-voice-video-and-real-time-the-webrtc-layer-you-inherit-fundamentals-stable-6b873310b7"]
links: ["skill-7-pick-the-architecture-by-what-you-re-willing-to-be-responsible-for-6a0db3a1e9"]
---

## 6. Libraries and starting points (all actively maintained as of 2026)

- `signalapp/libsignal-client` (Rust, AGPL) — the canonical stack, SPQR included
  ([repo](https://github.com/signalapp/SparsePostQuantumRatchet)).
- **libsodium** (C, bindings for every language) — the auxiliary primitives libsignal does not give
  you: AEAD (XChaCha20-Poly1305), X25519 key exchange, Ed25519 signatures, Argon2id password
  hashing, HMAC. Reach for it for everything *around* the ratchet; reach for your platform's TLS
  stack (BoringSSL, OpenSSL, rustls, Secure Transport) for transport, and never disable certificate
  verification to make a test pass.
- MLS: **OpenMLS** (Rust, Phoenix R&D), **mls-rs** (AWS, Rust) — both tracked by Wire/MIMI work.
- Matrix: `matrix-rust-sdk` + vodozemac (crypto incl. cross-signing, 4S backup), `matrix-js-sdk`,
  `mautrix-go` (appservices/bridges), matrix-nio (Python).
- XMPP: libomemo-c (Dino lineage), libomemo.js 2.0 (dual-version OMEMO), aioxmpp/slixmpp.
- SimpleX: simplexmq protocol crates/specs; Telegram: TDLib + Bot API SDKs (→ `chat-telegram`).
- Reference reading that transfers: Signal's engineering blog back-catalogue; RFC 9420; the
  Eurocrypt '25 / USENIX Sec '25 Triple-Ratchet papers; the Matrix spec; Albrecht et al. on
  MTProto for what bespoke protocols cost you.

---

# PART II — THE OPERATOR'S PLAYBOOK
