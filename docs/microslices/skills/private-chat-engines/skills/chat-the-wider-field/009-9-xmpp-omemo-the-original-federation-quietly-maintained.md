---
id: skill-9-xmpp-omemo-the-original-federation-quietly-maintained-a2f7ebb1a2
purpose: 9 xmpp omemo the original federation quietly maintained
source: src/vibey_tools/skills/plugins/private-chat-engines/skills/chat-the-wider-field/SKILL.md
requires: ["skill-8-nostr-the-pub-sub-protocol-that-accidentally-wants-to-be-a-messenger-7361d5f0a2"]
links: ["skill-10-briar-the-no-network-messenger-in-maintenance-mode-f7995e5b83"]
---

## 9. XMPP + OMEMO — the original federation, quietly maintained

The most mature self-hosting story of all (Prosody/ejabberd; Snikket for opinionated packaging).
OMEMO (XEP-0384 v0.3) is a Signal-derived double-ratchet E2EE done **purely client-side** — the
server has zero OMEMO knobs ([engineered.at ops account, Feb 2026](https://engineered.at/articles/running-my-own-xmpp-server)).
State of play: **OMEMO 2** (`urn:xmpp:omemo:2`) is rolling out early — Dino via libomemo-c already,
Converse.js's libomemo.js added dual-version support (Jun 2026, with interop vectors and
MAX_SKIP DoS hardening — [release](https://github.com/conversejs/libomemo.js/releases/tag/v2.0.0)),
and Conversations began SCE groundwork with NLnet/EC funding (Apr 2026 —
[announcement](https://nostr.ae/nevent1qqs89ktgxqer2jm9tch3z757qg9tc7xrl728mhh6gepsj9mgsq4dnvqzyqs9q2yr4n39veh6fhsjlahuqxe2dfj5mz0zsdpw653u85nzcj30cj5mgvr));
ecosystem steady (Prosody 13.0.x, ejabberd 26.01, per
[Jan 2026 XMPP newsletter](https://xmpp.org/2026/02/the-xmpp-newsletter-january-2026/)). Federation
metadata caveats: as Matrix, plus weaker defaults (OMEMO coverage is client-dependent).
