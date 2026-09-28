---
id: skill-6-simplex-the-no-identifiers-radical-94387cb375
purpose: 6 simplex the no identifiers radical
source: src/vibey_tools/skills/plugins/private-chat-engines/skills/chat-the-wider-field/SKILL.md
requires: ["skill-5-olvid-the-certification-play-e1adad2131"]
links: ["skill-7-session-onion-routed-messenger-on-crypto-incentivised-nodes-d47cd8f62d"]
---

## 6. SimpleX — the no-identifiers radical

The design statement: **no user identifiers at all** — no numbers, usernames, random IDs; every
conversation is reached via pairwise relay queues. SMP relays (Haskell, self-hostable) shuffle
ciphertexts between pairwise queues; XFTP handles chunked encrypted files; optional Tor/onion
transport. That single choice removes account enumeration, contact discovery and much of the
social graph problem — at a UX cost (adding people means out-of-band link exchange).

- **Crypto**: double-ratchet plus, since v5.6 (Mar 2024), **hybrid post-quantum** using
  **sntrup761 parallel-KEM augmentation inside every ratchet step** — break-in *recovery* is PQ,
  not just establishment (their deliberate one-up on PQXDH;
  [announcement](https://simplex.chat/blog/20240314-simplex-chat-v5-6-quantum-resistance-signal-double-ratchet-algorithm/) ·
  [RFC](https://github.com/simplex-chat/simplex-chat/blob/stable/docs/rfcs/2023-09-30-pq-double-ratchet.md);
  sntrup761x25519 itself is now [RFC 9941](https://www.rfc-editor.org/rfc/rfc9941.html), long the
  OpenSSH default).
- **2026 state (verified)**: 3M+ downloads, **480k+ MAU**, 1,000+ community-run servers, $650k in
  donations (incl. Vitalik Buterin), all built on $1.7M over four years
  ([Wefunder launch post, Aug 2026](https://simplex.chat/blog/20260819-simplex-chat-crowdfunding.html) ·
  [ITSFOSS](https://itsfoss.com/news/simplex-chat-investment-drive/) ·
  [crowdfunding page](https://simplex.chat/crowdfunding/)). v6.5 (Apr 2026) shipped **SimpleX
  Channels** (public broadcast: content visible to relays, poster identities private) and a
  **Network Consortium** governance model with Community Credits — an attempt to fund infra
  without ads or surveillance
  ([v6.5 post](https://simplex.chat/blog/20260430-simplex-channels-v6-5-consortium-crowdfunding-freedom-of-speech.html)).
- Operator story: run `smp-server`/`xftp-server`, contribute routing diversity; users bind
  per-contact queues to chosen servers.
