---
id: skill-5-developer-perspective-bb73117d03
purpose: 5 developer perspective
source: src/vibey_tools/skills/plugins/private-chat-engines/skills/chat-signal/SKILL.md
requires: ["skill-4-operator-perspective-there-is-no-signal-server-to-run-now-what-d6df0fdf73"]
links: ["skill-6-honest-weaknesses-say-them-out-loud-68f1fb6ffb"]
---

## 5. Developer perspective

- **The library**: [`libsignal-client`](https://github.com/signalapp/libsignal) (Rust, AGPL-3.0)
  is the reference implementation (protocol, zkgroup, SVR, account keys), with Java/Swift/Node
  bindings. Everything from the Double Ratchet to the SPQR machinery is readable — one of the
  best cryptography engineering educations available in any public repo (defensive serialisation,
  constant-time ops, formal-verification CI).
- **Protocol adoption ≠ free licence**: WhatsApp, Google Messages and FB Messenger use Signal
  Protocol under arrangement, not because AGPL is friendly. If you *build on* libsignal-client
  in a proprietary product you inherit AGPL obligations; design accordingly.
- **No official bot/service API**. Signal deliberately has none. The widely used unofficial
  path is `signal-cli` (third-party, links as a device; fine for personal automation, fragile
  and not sanctioned for service development). If your product needs a bot platform, that is
  Telegram's or Matrix's world (→ `chat-telegram`, `chat-matrix-and-element`).
- **What building "on Signal" really means**: you can't; you build *beside* it — Molly-style
  hardened clients, UnifiedPush plumbing, Signal-Protocol-based products with your own server
  (which WhatsApp-scale companies do; see `chat-builder-and-operator-playbooks` for the honest effort budget).
- **Engineering culture to steal**: every protocol change ships with a written design story
  (blog/papers), formal analysis, a heterogeneous-rollout+downgrade-migration plan, and code in
  Rust. The Triple Ratchet rollout (ignore-unknown-fields, MAC-protected downgrade window,
  future enforce-flag) is the canonical pattern for upgrading cryptography across a live fleet.

---
