---
id: skill-12-cross-chain-a5e9cc9aa6
purpose: 12 cross chain
source: src/vibey_tools/skills/plugins/cryptocurrency-development/skills/blockchain-protocol-layer/SKILL.md
requires: ["skill-11-layer-2-and-building-a-chain-54ab40b2d8"]
links: []
---

## §12. Cross-Chain

**[DURABLE] Bridges are the most-exploited category in the field's history, and the reason
is structural**: they hold concentrated value and must verify claims about a chain they
can't natively see.

**The models**: **lock-and-mint** (⚠️ the lockbox is a honeypot), **burn-and-mint**,
**liquidity networks**, **light-client / native verification** (the most secure, most
expensive), and **optimistic bridges**.

**The trust question to ask about any bridge**: *who attests that the source-chain event
happened?* A multisig? An external validator set? A light client? **A bridge secured by a
5-of-9 multisig has the security of a 5-of-9 multisig, regardless of what the marketing
says.**

**⚠️ Cross-chain message verification is where bridges break in practice.** A 2026 example:
an attacker crafted **fake Axelar messages that passed validation** and tricked a receiver
contract into releasing funds without a matching deposit — **missing access control in the
message receiver**, ~$3M across chains. The pattern (trusting an inbound message without
verifying the sender and the source chain) recurs constantly.

**Messaging protocols**: LayerZero, CCIP, Axelar, Wormhole, Hyperlane — each with a
different trust model you should be able to state in one sentence before integrating.
