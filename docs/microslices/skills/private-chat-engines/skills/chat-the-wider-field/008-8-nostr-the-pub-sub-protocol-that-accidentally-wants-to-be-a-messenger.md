---
id: skill-8-nostr-the-pub-sub-protocol-that-accidentally-wants-to-be-a-messenger-7361d5f0a2
purpose: 8 nostr the pub sub protocol that accidentally wants to be a messenger
source: src/vibey_tools/skills/plugins/private-chat-engines/skills/chat-the-wider-field/SKILL.md
requires: ["skill-7-session-onion-routed-messenger-on-crypto-incentivised-nodes-d47cd8f62d"]
links: ["skill-9-xmpp-omemo-the-original-federation-quietly-maintained-a2f7ebb1a2"]
---

## 8. Nostr — the pub/sub protocol that accidentally wants to be a messenger

Nostr's native DMs were famously weak (NIP-04 ECDH+AES-CBC: no forward secrecy, metadata in the
clear on relays). The 2025–26 answer is **the Marmot protocol / NIP-EE: MLS groups over Nostr
events** — KeyPackages as addressable events, gift-wrapped membership, FS/PCS semantics from MLS.
Flagship client **White Noise** ([whitenoise-rs](https://github.com/marmot-protocol/whitenoise-rs))
shipped audits (Least Authority), group chat, encrypted media (MIP-04), external signers and SDKs
in five languages through 2026 ([v2026.3.23 notes](https://njump.me/naddr1qqfhw6rfw3jj6mn0d9ek2ttkxgcryd3nx5q3wamnwvaz7tmjv4kxz7fwwpexjmtpdshxuet59upzqawhxlp5wfr3q2wyfpmtxvxj9ppg3fp80x6erghdfk4pcmq8a7hhqvzqqqr4gux747xs) ·
[NIP-EE spec](https://github.com/nostr-protocol/nips/blob/001c516f7294308143515a494a35213fc45978df/EE.md) ·
[Sovereign Engineering podcast #25](https://sovereignengineering.io/podcast/25-white-noise-mls-and-marmot-w-jeff-g)).
Interesting because: transport-agnostic, identity = keypair you already use socially, and MLS
gives it a real group crypto story no one else in web3-adjacent land has.
