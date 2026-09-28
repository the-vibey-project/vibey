---
id: skill-2-matrix-2-0-verified-and-where-it-stands-in-sept-2026-84446e49d5
purpose: 2 matrix 2 0 verified and where it stands in sept 2026
source: src/vibey_tools/skills/plugins/private-chat-engines/skills/chat-matrix-and-element/SKILL.md
requires: ["skill-1-the-protocol-fundamentals-stable-9c05e1c9e4"]
links: ["skill-3-the-ecosystem-organisations-money-and-who-s-maintaining-what-verified-f8dec783ce"]
---

## 2. Matrix 2.0 (verified) — and where it stands in Sept 2026

Announced/shipped as an *API contract* in October 2024
([Matrix.org](https://www.matrix.org/blog/2024/10/29/matrix-2.0-is-here/)), four pillars:

1. **Simplified Sliding Sync (MSC4186)** — instant login/launch/sync; implemented natively in
   Synapse ≥1.114, deprecating the old sync *proxy*. **Accepted by the Spec Core Team in mid-2026**
   ([TWIM 3 Jul 2026](https://matrix.org/blog/2026/07/03/this-week-in-matrix-2026-07-03/)).
2. **Native OIDC auth (MSC3861)** via the **Matrix Authentication Service (MAS)** — QR-code login,
   external IdPs, modern sessions. (Synapse dropped the experimental MSC3861 phase in favour of
   stable MAS integration in v1.157 cycle, [TWIM 17 Jul 2026](https://matrix.org/blog/2026/07/17/this-week-in-matrix-2026-07-17/)).
3. **MatrixRTC (MSC4143)** — native E2EE group voice/video; built on **Element Call + LiveKit SFU**;
   2026 additions: "slots" (real-time primitives for calls, games, virtual worlds), sticky events,
   a JS MatrixRTC SDK — demos include multiplayer Godot games running over federation
   ([Element blog, FOSDEM 2026](https://element.io/blog/exploring-matrixrtc-real-time-communication-in-rooms/)).
4. **Invisible Encryption** — eliminating the infamous "Unable to Decrypt" errors.

As of September 2026 the Spec Core Team was "aiming to cut" the formal 2.0 release
([TWIM 14 Aug 2026](https://matrix.org/blog/2026/08/14/this-week-in-matrix-2026-08-14/));
Element X clients were shipping 2.0 features incrementally (QR login, user status, live location).

**Federation stats (July 2026)**: ~19,512 known federating servers, **78.8% of them running
Synapse** — the federation's diversity problem in one number.

---
