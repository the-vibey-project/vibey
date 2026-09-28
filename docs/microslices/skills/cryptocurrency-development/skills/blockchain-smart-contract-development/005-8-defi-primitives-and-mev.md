---
id: skill-8-defi-primitives-and-mev-1b32e4d00f
purpose: 8 defi primitives and mev
source: src/vibey_tools/skills/plugins/cryptocurrency-development/skills/blockchain-smart-contract-development/SKILL.md
requires: ["skill-7-standards-c0759fdcf2"]
links: []
---

## §8. DeFi Primitives and MEV

### 8.1 The building blocks
**AMMs** (constant product `x·y=k`; concentrated liquidity; the **impermanent loss** that
LPs bear), **lending** (over-collateralization, health factors, liquidation incentives),
**stablecoins** (fiat-backed, over-collateralized crypto-backed, and algorithmic — ⚠️ the
last category has an extensive failure history), **derivatives**, and **liquid staking**.

**[DURABLE] Composability is the superpower and the risk.** Contracts calling contracts
calling contracts means your protocol's safety depends on dependencies you don't control,
and a bug three layers down can drain you.

### 8.2 Oracles

**[DURABLE] Oracle manipulation is a top-tier exploit class, and the fix is well known.**
```
⚠️ NEVER:   price = reserve1 / reserve0      // spot price from a DEX pool
                                              // — a flash loan moves it in one tx
✓  INSTEAD: Chainlink / Pyth / RedStone push or pull feeds
            TWAPs over a meaningful window
            multiple independent sources with deviation checks
```
And check the feed's own health: staleness (`updatedAt`), the L2 sequencer uptime feed,
and sane min/max bounds. **⚠️ A stale oracle reading treated as current is itself an
exploit** — several protocols have lost funds this way without any manipulation at all.

### 8.3 Flash loans

Uncollateralized loans that must be repaid in the same transaction. **[DURABLE] Flash loans
are not the vulnerability — they are the capital amplifier that makes an existing
vulnerability profitable.** They turn "an attacker with $100M could do this" into "anyone
can do this, right now, for a fee." **Assume every attacker has unlimited capital for one
transaction**, and your threat model becomes correct.

### 8.4 MEV

**[DURABLE]** Maximal Extractable Value — profit from ordering, inserting, or censoring
transactions. **Front-running**, **back-running**, **sandwich attacks** (the one that
directly harms ordinary users), **liquidations** and **arbitrage** (arguably beneficial).

**Mitigations for builders**: slippage limits and deadlines on every swap (**a swap with no
slippage bound is free money for a sandwicher**), commit-reveal schemes, batch auctions,
private mempools/order flow, and designing so ordering doesn't matter.

**The infrastructure**: proposer-builder separation currently runs through **out-of-protocol
relays** (MEV-Boost), which is a real centralization dependency — **which is precisely what
Glamsterdam's ePBS (§3.2 → `blockchain-protocol-layer`) is intended to bring in-protocol.**
