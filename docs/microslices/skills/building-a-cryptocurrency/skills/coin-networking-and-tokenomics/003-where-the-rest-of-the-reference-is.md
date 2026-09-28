---
id: skill-where-the-rest-of-the-reference-is-f75b18e9f6
purpose: where the rest of the reference is
source: src/vibey_tools/skills/plugins/building-a-cryptocurrency/skills/coin-networking-and-tokenomics/SKILL.md
requires: ["skill-8-economics-and-tokenomics-9d091dddba"]
links: []
---

## Where the rest of the reference is

- §1 → `coin-what-it-is-and-the-three-architectures` — block times, block sizes and supply
  policies of the three reference architectures, which set the parameters this part prices.
- §2 → `coin-cryptographic-primitives` — the hash functions that let `inv` announce a
  transaction or block by identifier rather than by payload.
- §3 → `coin-consensus-and-finality` — proof of work, proof of stake, slashing and fork choice;
  the security budget above is the economic face of those mechanisms.
- §4 → `coin-building-a-utxo-chain` — virtual bytes, transaction validation and the relay rules
  the mempool enforces.
- §5 → `coin-building-an-account-chain` — gas, the EVM, and the base-fee mechanics EIP-1559
  sits on top of.
- §6 → `coin-privacy-features` — Dandelion++ stem-phase broadcast, which is a networking
  change made for privacy reasons.
- §9–§10 → `coin-security-and-the-build-guide` — what actually loses money, and the ordered
  guide to building and launching a chain.
