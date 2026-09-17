---
name: coin-consensus-and-finality
description: "Use when choosing a consensus mechanism for a new chain, sizing confirmation counts before releasing value, reasoning about 51 percent attacks and chain reorganizations, tuning difficulty retargeting, picking a proof-of-work algorithm, or deciding between probabilistic, explicit and instant finality. Covers proof of work, proof of stake, Gasper, BFT and DAG designs, slashing, nothing-at-stake and validator economics. Part 3 of 8 of the Building a Cryptocurrency reference."
---

# Consensus Mechanisms and Finality

> **Part 3 of 8** of the *Building a Cryptocurrency* reference (plugin
> `building-a-cryptocurrency`), covering §3 — proof of work, proof of stake, Sybil resistance, fork choice and what finality actually means. Sibling skills:
> `coin-what-it-is-and-the-three-architectures` (§1 — the replicated-state-machine definition and the Bitcoin / Ethereum / Monero reference architectures),
> `coin-cryptographic-primitives` (§2 — the hashes, signatures, key derivation and commitment schemes a chain is built from),
> `coin-building-a-utxo-chain` (§4 — the UTXO ledger model, script, transaction validation and what a fork of Bitcoin actually involves),
> `coin-building-an-account-chain` (§5 — the account/world-state model, the EVM, gas, and building a chain with smart contracts),
> `coin-privacy-features` (§6 — ring signatures, stealth addresses, confidential amounts and zero-knowledge approaches),
> `coin-networking-and-tokenomics` (§7–§8 — peer-to-peer gossip and propagation, then issuance, fees, supply schedules and incentive design),
> `coin-security-and-the-build-guide` (§9–§10 — what actually loses money, and the ordered guide to building and launching a chain),
>
> Section numbers are **shared across the whole set**: a reference written as §N → `skill` points
> into that sibling skill. This is an engineering reference, **not investment, legal or tax advice** —
> deploying a chain that handles real value carries securities, AML/KYC and consumer-protection
> obligations that are a question for counsel in your jurisdiction.

## §3 Consensus Mechanisms: How the Network Agrees

Consensus is the heart of a cryptocurrency. It solves the problem of distributed agreement in a
network where **anyone can join, no one is trusted, and participants may be adversarial**. The
consensus mechanism determines how blocks are produced, how conflicts are resolved, and how the
network resists attacks.

Carried forward from the document's opening **SCOPE AND DISCLAIMER**: creating a cryptocurrency is a
legitimate software engineering exercise with well-documented open-source reference implementations,
but deploying one that handles real value carries serious legal, financial and security
responsibilities. Consult counsel regarding securities law, AML/KYC requirements and consumer
protection regulations in your jurisdiction before launching anything that distributes tokens to the
public. Choosing a consensus mechanism is where that exposure begins — it fixes who earns the
issuance and who can censor.

### §3.1 Proof of Work (PoW)

Mining is **Sybil-resistant leader election by burned energy**. Miners compete to find a nonce that
makes the hash of the block header fall below a difficulty target. The first miner to find a valid
hash gets to propose the next block and receives the block reward (new coins plus transaction fees).
The energy expenditure — **not identity** — is what makes rewriting history expensive: to reorganize
the chain, an attacker must redo the work for all blocks they want to replace, faster than the honest
network produces new ones.

```
Block hash = SHA256d(version || prev_block || merkle_root
|| timestamp || bits || nonce)
Valid if: block_hash < target
(where target is derived from the 'bits' field)
Difficulty retargets every N blocks to maintain target block time
```

Reproduced exactly as the source writes it. Note that the source elsewhere defines SHA-256d as
double SHA-256 (§2 → `coin-cryptographic-primitives`), so the nesting above reads as the source's own
shorthand rather than a third hashing pass.

**Difficulty adjustment.** The network periodically retargets the difficulty to keep the block
interval near the target, regardless of how much mining power joins or leaves. Bitcoin retargets
every **2,016 blocks (~2 weeks)** to hold **10-minute blocks**. If blocks are coming too fast,
difficulty increases; too slow, it decreases. This is a simple feedback loop, but it is **essential —
without it, the block interval would be chaotic**. *(Computed from those two figures: 2,016 × 10 min
= 20,160 minutes ≈ 14 days, which is the ~2 weeks the source states.)*

**Probabilistic finality.** PoW has **no explicit finality** — there is always a mathematical
possibility that a longer chain could be found. But each block on top of your transaction raises the
cost of rewriting history **exponentially**. Conventionally, **6 confirmations (blocks)** is treated
as settled for Bitcoin, but the right number depends on **the value at risk and the attacker's
hashpower**. For small payments, **1–3** may suffice; for enormous settlements, wait longer.

| Value at risk | Confirmations the source suggests |
|---|---|
| Small payments | 1–3 blocks may suffice |
| Conventional Bitcoin settlement | 6 confirmations, treated as settled |
| Enormous settlements | Wait longer than 6 — judge against attacker hashpower |

**The 51% attack reality.** A miner controlling **>50% of hashrate** can reorganize the chain,
double-spend, and censor transactions. But they **cannot** steal keys, create coins out of thin air,
or change the consensus rules. For small PoW chains, the **security budget** (what honest miners
earn) may be small enough that an attacker can rent or buy majority hashrate economically.

| Can a >50% attacker do this? | Answer |
|---|---|
| Reorganize the chain | Yes |
| Double-spend | Yes |
| Censor transactions | Yes |
| Steal keys | No |
| Create coins out of thin air | No |
| Change the consensus rules | No |

**Monero, 2025 — a worked example of a rented majority.** A project called **Qubic** paid miners more
than the block reward to mine XMR, achieving an estimated **28–35% hashrate share** and producing a
**6-block reorganization**. The lesson the source draws: **selfish mining can degrade a chain well
below the 51% threshold** — you do not need a majority to hurt a chain, and 28–35% was enough to
produce a reorg the length of Bitcoin's conventional settlement depth.

#### CHOOSING YOUR POW ALGORITHM

Your choice determines **who can mine and how decentralized your network is**. **ASIC resistance is an
arms race — Monero has changed its PoW algorithm multiple times to defeat ASICs.**

| Algorithm | Used by | Hardware profile | Consequence |
|---|---|---|---|
| **SHA-256d** | Bitcoin | Dominated by ASICs | Mining is industrial, but the network is very secure because the hardware cost of attack is enormous |
| **RandomX** | Monero | CPU-optimized, designed so that ASICs are uneconomic | Keeps mining decentralized on commodity hardware |
| **Ethash** | Old Ethereum, now deprecated | Memory-hard | A middle ground |

### §3.2 Proof of Stake (PoS)

Instead of burning energy, validators **bond capital (stake)**. The network selects a block proposer
**proportional to their stake** (or randomly among stakers). Misbehavior is punished by **slashing** —
the network destroys part of the validator's stake for provable offenses like **double-signing
(equivocation)**. Being offline is also penalized (**inactivity leaks**), though less severely.

**Ethereum's Gasper (post-Merge)** has two components:

| Component | What it does |
|---|---|
| **LMD-GHOST** | Fork choice — follow the heaviest subtree of attestations |
| **Casper FFG** | Finality — a checkpoint finalizes after **2/3 of staked ETH** attests, giving **explicit finality after two epochs, ~13 minutes** |

Validators stake **32 ETH**, attest to blocks each epoch, and occasionally propose blocks. This is the
**most battle-tested PoS design**, but it is also **complex — the spec is hundreds of pages**.

**The nothing-at-stake problem.** In PoW, mining on a losing chain wastes real energy. In PoS,
signing on multiple forks **costs nothing** (unless caught and slashed). The solution is slashing —
make the cost of equivocation **larger than the potential gain**. Ethereum's slashing destroys a
significant portion of the validator's stake **and ejects them from the validator set**.

**Validator economics.** PoS creates a tension between **decentralization** (many small validators)
and **efficiency** (fewer, larger validators). Ethereum requires **32 ETH per validator**, which is a
barrier. **Liquid staking (Lido, Rocket Pool)** lets users stake smaller amounts through
intermediaries, but this **concentrates stake with a few large operators — a real centralization
concern**.

### §3.3 BFT-Style Consensus

**Tendermint/CometBFT, HotStuff**, and similar designs give **instant finality**: once a block is
committed, it is final — **no reorganizations**. The trade-off is that they work well with **small
validator sets (dozens to low hundreds)** but **degrade with thousands**. If **more than 1/3 of
validators are offline or malicious, the chain halts**. These designs are popular for
**application-specific chains (Cosmos SDK)** where the validator set is known and managed.

**DAG-based and leaderless designs.** Several newer cryptocurrencies use **directed acyclic graph**
structures where transactions reference **multiple previous transactions**, enabling **parallel
processing**. These are **real but less battle-tested** than the three main families.

### §3.4 The families side by side

Derived from the §3 prose above; every cell traces to a sentence in this section.

| | **PoW** | **PoS** | **BFT (Tendermint/CometBFT, HotStuff)** | **DAG / leaderless** |
|---|---|---|---|---|
| **Sybil resistance** | Burned energy | Bonded capital (stake) | Known, managed validator set | Not stated in §3 |
| **Leader selection** | First to find a valid nonce | Proportional to stake, or random among stakers | Validator set voting | Leaderless |
| **Finality** | Probabilistic — no explicit finality | Explicit — Casper FFG after two epochs, ~13 min | Instant — no reorganizations once committed | Not stated in §3 |
| **Misbehavior penalty** | Wasted energy on a losing chain | Slashing; inactivity leaks for being offline | Not stated in §3 | Not stated in §3 |
| **Scale profile** | Global, open participation | Global, but 32 ETH per validator is a barrier | Dozens to low hundreds; degrades with thousands | Parallel processing of transactions |
| **Liveness failure** | Chain continues; reorgs possible | Not stated in §3 | Halts if >1/3 of validators are offline or malicious | Not stated in §3 |
| **Maturity** | Most proven | Most battle-tested PoS design, but complex | Popular for application-specific chains (Cosmos SDK) | Real but less battle-tested |

**What "finality" actually means here.** Three distinct guarantees, and they are not interchangeable:

| Finality model | Guarantee | Where it comes from |
|---|---|---|
| **Probabilistic** | No explicit finality; each additional block raises the cost of rewriting history exponentially | PoW — settled by convention at 6 confirmations for Bitcoin |
| **Explicit** | A checkpoint is finalized once 2/3 of staked ETH attests — ~13 minutes, two epochs | PoS via Casper FFG |
| **Instant** | Once committed, final; no reorganizations | BFT-style consensus |

### §3.5 Choosing, from the source's own arguments

Synthesis of §3 above with the consensus decision framing the source states in §1; no claim here goes
beyond what those two sections say.

- **The trade-off that never goes away** (stated in §1 → `coin-what-it-is-and-the-three-architectures`,
  and the reason this section exists): decentralization, security and scalability pull against each
  other, and every design picks a point on that triangle.
- **Pick PoW** when you want simplicity and robustness and can accept energy intensity (§1 calls PoW
  simple, robust and energy-intensive) — and then pick
  the algorithm for the mining population you want (ASIC-dominated SHA-256d for hardware-cost
  security, RandomX for commodity-hardware decentralization), knowing ASIC resistance is a permanent
  arms race.
- **Pick PoS** when you want energy efficiency and explicit finality, and accept the complexity §1
  names — slashing, validator management, nothing-at-stake — plus the centralizing pull of liquid
  staking.
- **Pick BFT** when instant finality matters more than open participation and the validator set is
  known and managed — and accept that it scales poorly beyond small validator sets, and that the
  chain halts if more than 1/3 of it goes bad or offline.
- **Size your security budget before launch.** On a small PoW chain the honest-miner revenue *is* the
  attack price; the Qubic/Monero episode shows an attacker paying above the block reward can buy
  28–35% of hashrate and reorg 6 blocks. Confirmation counts are a function of that budget, not a
  constant.
