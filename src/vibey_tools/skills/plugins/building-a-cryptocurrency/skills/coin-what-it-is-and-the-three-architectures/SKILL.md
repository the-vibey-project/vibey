---
name: coin-what-it-is-and-the-three-architectures
description: "Use when choosing a ledger model, consensus mechanism, programmability level, privacy model or supply schedule for a new chain, when you need the Bitcoin, Ethereum and Monero reference architectures compared cell by cell, or when you need the precise definition of what a blockchain is before designing one. Covers the replicated-state-machine definition and the five upstream decisions that cascade into every downstream implementation choice. Part 1 of 8 of the Building a Cryptocurrency reference."
---

# What a Cryptocurrency Actually Is

> **Part 1 of 8** of the *Building a Cryptocurrency* reference (plugin
> `building-a-cryptocurrency`), covering §1 — the replicated-state-machine definition and the Bitcoin / Ethereum / Monero reference architectures. Sibling skills:
> `coin-cryptographic-primitives` (§2 — the hashes, signatures, key derivation and commitment schemes a chain is built from),
> `coin-consensus-and-finality` (§3 — proof of work, proof of stake, Sybil resistance, fork choice and what finality actually means),
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

## §1 What a Cryptocurrency Actually Is

### 1.0 Scope and disclaimer (carried forward from the source document)

> **SCOPE AND DISCLAIMER**
>
> This is an engineering reference, not investment advice. Creating a cryptocurrency is a
> legitimate software engineering exercise with well-documented open-source reference
> implementations. However: deploying a cryptocurrency that handles real value carries
> serious legal, financial, and security responsibilities. **Consult counsel regarding
> securities law, AML/KYC requirements, and consumer protection regulations in your
> jurisdiction before launching anything that distributes tokens to the public.**

This part of the reference decides supply schedules, privacy models and distribution
posture. Every one of those five decisions (§1.4) has a legal surface, not just a technical
one — carry the disclaimer above into any launch discussion. The whole reference covers
the cryptographic primitives, consensus mechanisms, ledger models, smart contract
platforms, privacy features, networking, economics, and security of cryptocurrency design,
with enough detail to build your own coin in the style of Bitcoin, Ethereum, or Monero.

### 1.1 The definition

A cryptocurrency is a **replicated state machine with Sybil-resistant leader election and a
fork-choice rule**, producing eventual (or explicit) agreement on an ordered log of
transactions. Everything else — the token, the wallets, the smart contracts, the governance
— is built on top of that foundation.

> **THE CORE DEFINITION**
>
> A blockchain is a **replicated ledger** (every node has a copy), ordered by a **consensus
> mechanism** (how everyone agrees on the next block), with **Sybil resistance** (making it
> expensive to create fake identities to take over the network), and a **fork-choice rule**
> (what happens when two valid blocks conflict). The "crypto" in cryptocurrency is the
> cryptographic primitives that make the ledger tamper-evident and the identities
> key-based rather than name-based.

The four components of that definition, and where each is developed:

| Component | What it does | Developed in |
|---|---|---|
| Replicated ledger | Every node has a copy | §4 → `coin-building-a-utxo-chain`, §5 → `coin-building-an-account-chain` |
| Consensus mechanism | How everyone agrees on the next block | §3 → `coin-consensus-and-finality` |
| Sybil resistance | Makes it expensive to create fake identities to take over the network | §3 → `coin-consensus-and-finality` |
| Fork-choice rule | What happens when two valid blocks conflict | §3 → `coin-consensus-and-finality` |
| Cryptographic primitives | Make the ledger tamper-evident and identities key-based rather than name-based | §2 → `coin-cryptographic-primitives` |

### 1.2 Understanding this section

Every major cryptocurrency is a variation on one of three architectural models, and
understanding them deeply is the foundation for designing your own. The table in §1.3 is
the reference grid; the five questions in §1.4 are what you answer before writing a line of
code.

### 1.3 The three reference architectures

| Property | Bitcoin ($BTC) | Ethereum ($ETH) | Monero ($XMR) |
|---|---|---|---|
| **Ledger model** | UTXO (unspent outputs) | Account (balances + code) | UTXO (privacy-enhanced) |
| **Consensus** | Proof of Work (SHA-256d) | Proof of Stake (Gasper) | Proof of Work (RandomX) |
| **Finality** | Probabilistic (confirmations) | Explicit (~13 min, Casper FFG) | Probabilistic (confirmations) |
| **Programmability** | Script (not Turing-complete) | EVM (Turing-complete) | None (no smart contracts) |
| **Privacy** | Pseudonymous (transparent ledger) | Pseudonymous (transparent ledger) | Mandatory privacy (hidden sender, receiver, amount) |
| **Supply** | Capped at ~21M | No cap (issuance schedule) | Tail emission (0.6 XMR/block forever) |
| **Block time** | ~10 minutes | ~12 seconds | ~2 minutes |
| **Block size** | ~1-4 MB (weight-limited) | Dynamic (gas limit, ~36M gas) | Dynamic (expands under demand) |

Named parameters and mechanisms in that grid, kept exactly as given: **SHA-256d** and
**RandomX** as proof-of-work functions; **Gasper** as Ethereum's proof-of-stake consensus
and **Casper FFG** as its finality gadget with an explicit ~13-minute finality; the **EVM** as
the Turing-complete virtual machine; Monero's **0.6 XMR/block** perpetual tail emission;
Bitcoin's **~21M** cap; Ethereum's **~36M gas** block limit; and Bitcoin's **weight-limited**
~1-4 MB blocks. Two of the three architectures (Bitcoin, Monero) are UTXO chains; Monero
is the privacy-enhanced variant, not a different ledger family.

### 1.4 Key design decisions you must make

Before writing a line of code, you need to answer these questions, because each one
cascades into dozens of implementation decisions downstream.

**1. Ledger model: UTXO or Account?**
UTXO (Bitcoin) means transactions consume and create discrete outputs — parallelizable,
simpler to verify, but no persistent state. Account (Ethereum) means persistent balances
and code — enables smart contracts, but every node must re-execute every transaction.
**This is the most fundamental architectural choice.** (§4 → `coin-building-a-utxo-chain`;
§5 → `coin-building-an-account-chain`)

**2. Consensus mechanism: PoW, PoS, or BFT?**
PoW is simple, robust, and energy-intensive. PoS is energy-efficient but adds complexity
(slashing, validator management, nothing-at-stake). BFT gives instant finality but scales
poorly beyond small validator sets. **The trade-off that never goes away: decentralization,
security, and scalability pull against each other, and every design picks a point on that
triangle.** (§3 → `coin-consensus-and-finality`)

**3. Programmability: none, limited script, or full VM?**
No programmability (Monero) is simplest and most secure. Limited script (Bitcoin) enables
multisig, timelocks, and payment channels without the attack surface of a full VM. A full
virtual machine (Ethereum) enables arbitrary smart contracts — **but every function is
callable by anyone, in any order, at any time, by attackers who read your source.**
(§5 → `coin-building-an-account-chain`; §9 → `coin-security-and-the-build-guide`)

**4. Privacy: transparent, optional, or mandatory?**
Transparent (Bitcoin/Ethereum) is simplest and most compliant but exposes all transaction
history. Optional privacy (Zcash shielded transactions) splits the anonymity set. Mandatory
privacy (Monero) gives uniform protection but creates regulatory friction — **most
regulated exchanges will delist you.** (§6 → `coin-privacy-features`)

**5. Supply: capped, scheduled, or infinite?**
Capped (Bitcoin's 21M) creates scarcity but **relies entirely on transaction fees for
long-term security once mining subsidies end.** Scheduled issuance (Ethereum) funds
validators indefinitely. Tail emission (Monero) provides perpetual miner revenue at the cost
of permanent low inflation. (§8 → `coin-networking-and-tokenomics`)

### 1.5 The five decisions at a glance

Restated from §1.4 — the options and the stated consequence of each.

| Decision | Options | What each buys you | What it costs you |
|---|---|---|---|
| **1. Ledger model** | UTXO (Bitcoin) | Parallelizable, simpler to verify | No persistent state |
| | Account (Ethereum) | Persistent balances and code; enables smart contracts | Every node must re-execute every transaction |
| **2. Consensus** | PoW | Simple, robust | Energy-intensive |
| | PoS | Energy-efficient | Complexity: slashing, validator management, nothing-at-stake |
| | BFT | Instant finality | Scales poorly beyond small validator sets |
| **3. Programmability** | None (Monero) | Simplest and most secure | No smart contracts |
| | Limited script (Bitcoin) | Multisig, timelocks, payment channels, without the attack surface of a full VM | Not a full VM; no arbitrary smart contracts |
| | Full VM (Ethereum) | Arbitrary smart contracts | Every function callable by anyone, in any order, at any time, by attackers who read your source |
| **4. Privacy** | Transparent (Bitcoin/Ethereum) | Simplest and most compliant | Exposes all transaction history |
| | Optional (Zcash shielded transactions) | Shielded transactions alongside transparent ones | Splits the anonymity set |
| | Mandatory (Monero) | Uniform protection | Regulatory friction; most regulated exchanges will delist you |
| **5. Supply** | Capped (Bitcoin, 21M) | Scarcity | Relies entirely on transaction fees for long-term security once mining subsidies end |
| | Scheduled issuance (Ethereum) | Funds validators indefinitely | No cap |
| | Tail emission (Monero) | Perpetual miner revenue | Permanent low inflation |

### 1.6 How to use §1

- Answer the five questions in §1.4 **first**. Each cascades into dozens of implementation
  decisions downstream, so a late reversal is not a refactor — it is a different chain.
- Pick the reference architecture in §1.3 whose row of answers is closest to yours, and read
  the corresponding build skill: UTXO → §4 → `coin-building-a-utxo-chain`; account/EVM →
  §5 → `coin-building-an-account-chain`; mandatory privacy → §6 → `coin-privacy-features`.
- Treat decisions 4 and 5 as having a legal surface as well as a technical one, and re-read
  §1.0 before doing anything that distributes tokens to the public.
