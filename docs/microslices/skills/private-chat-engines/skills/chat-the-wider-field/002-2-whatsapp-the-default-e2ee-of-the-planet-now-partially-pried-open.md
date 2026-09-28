---
id: skill-2-whatsapp-the-default-e2ee-of-the-planet-now-partially-pried-open-3a3336804e
purpose: 2 whatsapp the default e2ee of the planet now partially pried open
source: src/vibey_tools/skills/plugins/private-chat-engines/skills/chat-the-wider-field/SKILL.md
requires: ["skill-1-mls-rfc-9420-and-wire-the-standards-track-finally-ships-e64265a4dd"]
links: ["skill-3-apple-imessage-the-post-quantum-pacesetter-3c0dc9effc"]
---

## 2. WhatsApp — the default E2EE of the planet, now partially pried open

Signal-Protocol E2EE by default for ~3 billion users; Noise-pipe transport; sealed-sender-ish
delivery; key-transparency-backed automatic security-code verification (2023); encrypted backups
(opt-in, password/64-digit key). Real caveats that persist: **metadata is Meta's** (no sealed
sender equivalent for graph privacy), account is phone-number-rooted, and "view once"
/disappearing messages are policy features on a surveilled-by-design platform edge.

**The 2024–2026 story is DMA interoperability** (verified):
- Meta, as a designated gatekeeper, must interoperate with third parties at no charge; phase 1
  (1:1 text + files) shipped on deadline, **and in November 2025 the first two third-party
  services — BirdyChat and Haiket — actually went live** with WhatsApp interop in the EEA
  ([EC developer portal](https://digital-markets-act.ec.europa.eu/developer-portal/messaging-interoperability_en) ·
  [Meta's interop explainer (Sep 2024)](https://about.fb.com/news/2024/09/an-update-on-how-were-building-safe-and-secure-third-party-chats-for-users-in-europe/) ·
  [byteiota's launch coverage](https://byteiota.com/whatsapp-eu-interoperability-third-party-messaging-goes-live/)).
- Requirements: Signal Protocol (or equivalent) E2EE with a free Meta sub-license option;
  opt-in user toggle ("Third-party chats"); mobile-only so far; groups due Sep 2025 (rollout
  dragging into 2026), calls due Sep 2027.
- **BEREC's opinion (Mar 2025)** on Meta's reference offers reads like a regulator noticing
  compliance-theatre: no multi-device, manual discovery, vague SLAs, broad Meta termination
  rights, an odd 60-day-EEA-presence rule
  ([BEREC BoR (25) 21](https://www.berec.europa.eu/system/files/2025-03/BoR%20(25)%2021%20BEREC%20Opinion%20on%20Meta's%20reference%20offers.pdf)).
- Neither Signal nor Telegram has requested interop; **May 3, 2026** was the EC's deadline to
  reappraise iMessage's non-designation (outcome not verified in this dossier).
- **Post-quantum: unverified.** One "SignalX-256" article found in research has the hallmarks of
  AI-fabricated content and matches no official announcement; treat WhatsApp as *not* PQ until
  Meta says otherwise credibly.
