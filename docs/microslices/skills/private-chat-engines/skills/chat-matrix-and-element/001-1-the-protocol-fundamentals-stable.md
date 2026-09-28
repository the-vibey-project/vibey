---
id: skill-1-the-protocol-fundamentals-stable-9c05e1c9e4
purpose: 1 the protocol fundamentals stable
source: src/vibey_tools/skills/plugins/private-chat-engines/skills/chat-matrix-and-element/SKILL.md
requires: []
links: ["skill-2-matrix-2-0-verified-and-where-it-stands-in-sept-2026-84446e49d5"]
---

## 1. The protocol (fundamentals — stable)

### 1.1 The data model: rooms as replicated event DAGs
A Matrix "room" is not a file on a server; it is a **partially-replicated directed acyclic graph
of signed JSON events** shared by every homeserver with a participating user. Message events,
membership changes, power levels, redactions — all events in the DAG. Each server keeps the full
history for the rooms it's in and resolves forks with **state resolution** (versioned algorithms;
"state res v2" is the modern one. Room **version 12** — being marched toward default as of mid
2026 — even redefines `room_id` as a hash of the create event, killing server-name dependence for
room identity).

### 1.2 Federation
Servers speak the **Server-Server API** over mutually-authenticated HTTPS with **signing keys**;
discovery via `.well-known` and SRV. Any server can join any joinable room (subject to room ACLs).
Federation is also the privacy caveat: *every participating server stores every (encrypted) event,
room state, and metadata for its users' rooms forever unless retention is configured* — see §4.6.

### 1.3 E2EE: Olm & MegOlm on vodozemac
- **Olm** (double-ratchet 1:1 sessions, X3DH-style one-time keys published to the server) and
  **MegOlm** (an *outbound-only* ratchet for group messages: one symmetric session per sender per
  room, shared to devices via Olm). The reference implementation is now **vodozemac** (Rust,
  formally audited, built with Cryspen) replacing the old C++ libolm in maintained clients.
- **Post-compromise security caveat**: because MegOlm sessions are outbound-only, they don't
  self-heal the way pairwise ratchets do; rotation settings and device-change sharing rules are
  the mitigation. This is a known, documented trade (cheap fan-out vs. weaker PCS).
- **History on join is a policy decision, not a protocol guarantee**: a joining device receives the
  current outbound session, so unless the room key has rotated it can decrypt messages already sent
  in that session. Set `m.room.history_visibility` and the rotation parameters
  (`rotation_period_ms` / `rotation_period_msgs` in `m.room.encryption`) deliberately rather than
  inheriting defaults — and state the answer in the room's description, because members will assume
  the opposite of whatever you chose.
- **Cross-signing & verification**: users hold master/self-signing/user-signing keys (secured by
  the "secure secret storage"/(4S) backup on the homeserver, protected by a recovery key);
  verification by QR/emoji between devices; the Matrix 2.0-era direction is **invisible
  encryption** — excluding unverified devices and moving toward trust-on-first-use — and the
  **Matrix 3.0 candidate is MLS** (per the [Matrix 2.0 announcement](https://www.matrix.org/blog/2024/10/29/matrix-2.0-is-here/)).

### 1.4 The spec process
MSC (Matrix Spec Change) → Spec Core Team review → spec releases (v1.14 era → **v1.19 expected
imminently**, mid-2026). Amusingly political live question as of 2026: **MSC4504 proposes a
single global "v2" version number** for the whole spec.

---
