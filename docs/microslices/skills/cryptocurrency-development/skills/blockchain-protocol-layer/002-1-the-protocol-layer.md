---
id: skill-1-the-protocol-layer-a8e23e2532
purpose: 1 the protocol layer
source: src/vibey_tools/skills/plugins/cryptocurrency-development/skills/blockchain-protocol-layer/SKILL.md
requires: ["skill-0-routing-92a8c8081a"]
links: ["skill-2-nodes-and-clients-c48cfe2369"]
---

## §1. The Protocol Layer

### 1.1 What a blockchain actually is

**[DURABLE]** A replicated state machine with **Sybil-resistant leader election** and a
**fork-choice rule**, producing eventual (or explicit) agreement on an ordered log.
Everything else is engineering detail.

```
mempool → block proposer selected → block built → propagated
  → validated by every node independently → fork choice → finality
```

**Consensus families:**
- **Proof of Work** — Sybil resistance by burned energy. Probabilistic finality (confirmations).
  Simple, robust, expensive. Bitcoin.
- **Proof of Stake** — Sybil resistance by bonded capital, with **slashing** for provable
  misbehaviour. Ethereum uses **Gasper** (LMD-GHOST fork choice + Casper FFG finality),
  giving **explicit finality** after two epochs (~13 minutes).
- **BFT-style** (Tendermint/CometBFT, HotStuff derivatives) — instant finality, smaller
  validator sets, liveness fails if >1/3 are offline.
- **DAG / leaderless** and other designs — real, less battle-tested.

**[DURABLE] The trade-off that never goes away**: decentralization, security, and
scalability pull against each other, and every design picks a point. **Be suspicious of any
claim to have escaped it** — usually the escape is a validator set small enough to be a
distributed database with extra steps.

### 1.2 Ethereum's post-Merge architecture

```
┌─────────────────────────┐        ┌──────────────────────────┐
│ CONSENSUS CLIENT        │ Engine │ EXECUTION CLIENT         │
│ (beacon chain, PoS)     │◄──API─►│ (EVM, state, mempool)    │
│ Lighthouse, Prysm, Teku,│        │ Geth, Nethermind, Reth,  │
│ Nimbus, Lodestar,       │        │ Besu, Erigon, ethrex     │
│ Grandine                │        │                          │
└─────────────────────────┘        └──────────────────────────┘
```
**[DURABLE] You must run both.** This split, formalized at The Merge (September 2022), is
the single most important structural fact about running Ethereum infrastructure, and it
surprises people who last looked before 2022.

**Validator economics**: 32 ETH per validator (**EIP-7251 raised the effective max balance
to 2048 ETH**, allowing consolidation), duties are attesting and occasionally proposing,
and **slashing** punishes provable equivocation while **inactivity leaks** punish being
offline during non-finality.

### 1.3 Client diversity — a genuine systemic risk

**[DURABLE] If one client runs a supermajority of validators, a bug in it can finalize an
invalid chain or cause mass slashing.** The thresholds that matter: **>1/3 breaks
finality; >2/3 can finalize a bad chain.** This is not theoretical — **Reth suffered a
severe network-wide outage on 2 September 2025** processing a specific block, taking down
most Reth nodes on mainnet; operators running a multi-client setup stayed up.

**[VERSIONED]** Execution-layer diversity has genuinely improved. Geth's share has fallen
from a historic ~84% to roughly **36–41%**, with **Nethermind ~23–32%**, **Reth ~14–15%**,
**Besu ~7–12%**, and **Erigon ~2–5%** depending on the measurement source. ⚠️ **The
sources disagree substantially** because they measure different populations (peer-visible
nodes vs. self-reported validators vs. staking-community surveys) — one 2026 staking survey
found **Nethermind ~45%, Geth ~33%, Besu ~15%** within that community. **The consensus
layer is the bigger worry**, with Lighthouse and Prysm both large.

**⚠️ If you run validators, run a minority client, and consider running more than one.**
This is the rare case where the socially responsible choice is also the operationally
safer one.

---
