---
id: skill-7-session-onion-routed-messenger-on-crypto-incentivised-nodes-d47cd8f62d
purpose: 7 session onion routed messenger on crypto incentivised nodes
source: src/vibey_tools/skills/plugins/private-chat-engines/skills/chat-the-wider-field/SKILL.md
requires: ["skill-6-simplex-the-no-identifiers-radical-94387cb375"]
links: ["skill-8-nostr-the-pub-sub-protocol-that-accidentally-wants-to-be-a-messenger-7361d5f0a2"]
---

## 7. Session — onion-routed messenger on crypto-incentivised nodes

Fork-of-Signal lineage with accounts = keypairs (no phone), messages onion-routed through
~1.5–2k service nodes and stored in **swarms** for offline delivery; **blinded account IDs**
hide recipient keys from nodes. Known weakness: Session's original protocol lacked **perfect
forward secrecy** — hence **Session Protocol v2** (PFS + PQ) in development, planned to debut via
the paid **Session Pro** beta
([Session dev update](https://getsession.org/session-development-update-pro-beta-protocol-v2)).

Verified network history:
- **21 May 2025**: migrated off the Oxen L1 to the **Session Network** with **$SESH on Arbitrum**;
  node staking = 25,000 SESH
  ([migration note](https://getsession.org/migrating-from-the-oxen-network-to-session-network) ·
  [Decrypt coverage](https://decrypt.co/321295/decentralized-messenger-session-goes-live-on-arbitrum-with-sesh-token-launch));
  node upgrade **11.6.0** introduced **Session Router**, a Lokinet rewrite for speed
  ([node upgrade post](https://token.getsession.org/blog/node-upgrade-11-6-0)).
- **2026 near-death**: the Session Technology Foundation paused development and laid off staff;
  community donations rescued it; a 2–3-person team now pushes consolidation into **libsession**,
  the Pro Beta, and Protocol v2 ([The Future of Session](https://getsession.org/the-future-of-session)).
  Read this as: the tech is real, the funding model is crypto-cyclical, caveat emptor.
