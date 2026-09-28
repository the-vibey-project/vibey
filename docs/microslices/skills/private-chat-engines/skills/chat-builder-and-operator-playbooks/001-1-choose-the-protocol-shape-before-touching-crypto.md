---
id: skill-1-choose-the-protocol-shape-before-touching-crypto-de285f9273
purpose: 1 choose the protocol shape before touching crypto
source: src/vibey_tools/skills/plugins/private-chat-engines/skills/chat-builder-and-operator-playbooks/SKILL.md
requires: []
links: ["skill-2-the-cryptography-stack-as-checklists-ae51596a6c"]
---

## 1. Choose the protocol shape before touching crypto

| Decision | Options | When each is right |
|---|---|---|
| Group crypto | Double Ratchet + sender keys (Signal/WhatsApp/OMEMO) | groups ≤ few thousand; strongest per-message FS/PCS |
| | **MLS (RFC 9420, TreeKEM)** | large or dynamic groups; standards interop (MIMI, DMA); O(log n) membership ops |
| | MegOlm-style outbound ratchets (Matrix) | cheap fan-out where weak PCS is acceptable and rotation is configured |
| | Pairwise queues, no group crypto (SimpleX) | metadata minimalism above all |
| Delivery | Server-mediated queues | async UX, offline delivery, multi-device |
| | Onion-routed swarms (Session) | network-level unlinkability; latency/storage complexity tax |
| | P2P/direct (Briar, calls) | no server trust; battery/NAT/nat-relay pain |
| Identity | Phone number (Signal/WhatsApp) | viral adoption, abuse control; leaks a government-traceable root |
| | Keypair-only (Session, Nostr, SimpleX) | maximal deniability; discovery UX becomes your problem |
| | Random short ID (Threema) / email (Wire/Delta) | middle paths with existing account rails |

> **⚠️ IF YOU HAVE NO STRONG REASON TO FEDERATE, START CENTRALISED.** The engineering effort is
> roughly **5–10× lower**, the security model is coherent, and one team can ship a protocol upgrade
> to the whole fleet — Signal shipped the Triple Ratchet in weeks; Matrix's E2EE changes take years
> (→ `chat-signal` §4, `chat-matrix-and-element` §2). Federation can be added later; it cannot be
> removed later. It is the right answer for an open communications commons, not for a private system
> where you control the trust model and carry the consequences — and the real bill is state
> replication, cross-server key distribution and split-brain, not the protocol itself
> (→ `chat-matrix-and-element` §4 for what you are signing up to).
