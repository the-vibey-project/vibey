---
name: coin-networking-and-tokenomics
description: "Use when designing or debugging the peer-to-peer layer of a chain — DNS seeds, peer exchange, inv and getdata gossip, compact block relay, mempool and relay policy — or when setting issuance, supply caps, tail emission, fee markets, token distribution and the security budget. Covers the policy versus consensus distinction and the trade-offs of each distribution method. Part 7 of 8 of the Building a Cryptocurrency reference."
---

# The Networking Layer, Economics and Tokenomics

> **Part 7 of 8** of the *Building a Cryptocurrency* reference (plugin
> `building-a-cryptocurrency`), covering §7–§8 — peer-to-peer gossip and propagation, then issuance, fees, supply schedules and incentive design. Sibling skills:
> `coin-what-it-is-and-the-three-architectures` (§1 — the replicated-state-machine definition and the Bitcoin / Ethereum / Monero reference architectures),
> `coin-cryptographic-primitives` (§2 — the hashes, signatures, key derivation and commitment schemes a chain is built from),
> `coin-consensus-and-finality` (§3 — proof of work, proof of stake, Sybil resistance, fork choice and what finality actually means),
> `coin-building-a-utxo-chain` (§4 — the UTXO ledger model, script, transaction validation and what a fork of Bitcoin actually involves),
> `coin-building-an-account-chain` (§5 — the account/world-state model, the EVM, gas, and building a chain with smart contracts),
> `coin-privacy-features` (§6 — ring signatures, stealth addresses, confidential amounts and zero-knowledge approaches),
> `coin-security-and-the-build-guide` (§9–§10 — what actually loses money, and the ordered guide to building and launching a chain),
>
> Section numbers are **shared across the whole set**: a reference written as §N → `skill` points
> into that sibling skill. This is an engineering reference, **not investment, legal or tax advice** —
> deploying a chain that handles real value carries securities, AML/KYC and consumer-protection
> obligations that are a question for counsel in your jurisdiction.

## §7 The Networking Layer

A cryptocurrency is a peer-to-peer network. **There is no central server.** Nodes discover each
other, maintain connections, gossip transactions and blocks, and independently validate
everything they receive. The networking layer is often underappreciated but is critical to the
system's resilience.

### P2P architecture

**Discovery.** Nodes find peers through three mechanisms:

| Mechanism | How it works |
|---|---|
| DNS seed lists | Hardcoded hostnames that resolve to known node IP addresses |
| Hardcoded IP lists | Fallback when DNS seeds are unavailable |
| Peer exchange | Nodes tell each other about other nodes they know |

New nodes bootstrapping onto the network use these mechanisms to find their first connections.

**Message types.** The wire protocol is a small set of messages:

| Message | Purpose |
|---|---|
| Version handshake | Negotiate protocol version and capabilities |
| `addr` | Share peer addresses |
| `inv` | Announce new transactions or blocks **by hash** — the recipient requests full data only if they do not already have it |
| `getdata` | Request the full payload for an announced hash |
| `tx`, `block` | Full payload |
| `ping` / `pong` | Keepalive and latency measurement |

The `inv` → `getdata` split is the bandwidth-saving core of the design: announce the hash
first, transfer the object only on demand.

**Block propagation.** When a miner finds a block, they broadcast it to their peers, who
validate it and relay it to their peers. **Compact block relay (BIP-152)** sends only the block
header and short transaction IDs, letting peers that already have most transactions
reconstruct the block without downloading full transactions they already know. This
minimizes bandwidth and reduces the time for blocks to propagate globally — important
because **slow propagation increases orphan rates and centralization pressure**. A miner who
hears about a block late wastes work on a stale tip; large, well-connected miners suffer that
less, which is why propagation latency is a decentralization problem and not merely a
performance one.

**Mempool.** Each node maintains a mempool of valid but unconfirmed transactions. When a
node receives a transaction it validates it — proper signatures, inputs exist and are unspent,
no double-spend — and if valid, adds it to the mempool and relays it. Miners select
transactions from their mempool to include in blocks, typically prioritizing by **fee rate
(satoshis per virtual byte)**.

> **The mempool is not shared state.** Each node has its own, and they can differ based on
> relay policy. Do not design anything that assumes two nodes see the same set of pending
> transactions.

### POLICY VS. CONSENSUS

What a node will **relay** (policy) and what the network will **accept in a block** (consensus)
are different rule sets. A node might refuse to relay transactions with very low fees, but still
accept a block containing them.

This distinction is **the actual constitution of blockchain governance** — policy changes can
split the mempool without splitting the chain. Bitcoin's 2025 v30 fight over `OP_RETURN`
defaults was a policy change, not a consensus change, and it was the sharpest governance
clash since the block-size wars.

Design consequence: a policy knob is a low-stakes lever you can turn per node and ship
without coordination; a consensus rule is a fork. Know which one you are touching before you
change a default.

## §8 Economics and Tokenomics

The economic design of a cryptocurrency is as important as the technical design. **Get it wrong
and the chain is insecure, abandoned, or both.** The economic model determines how security
is funded, how the token is distributed, and what incentives participants have to act honestly.

### Supply and distribution design

| Model | Mechanism | Long-run security funding | Trade-off |
|---|---|---|---|
| **Fixed cap** (Bitcoin) | 21M coins, halving every ~4 years; mining subsidy starts at 50 BTC/block and halves until it reaches zero (~2140) | Transaction fees only, after the subsidy ends | If fee revenue is insufficient, the security budget collapses and the chain becomes cheap to attack. **This is an unsolved long-term problem.** |
| **Tail emission** (Monero) | After the main emission curve ends, a perpetual **0.6 XMR per block** continues forever (~0.87% annual inflation, declining as supply grows) | Miners are always funded without relying on fee revenue | No hard cap, which some investors find unappealing |
| **Scheduled issuance** (Ethereum) | No hard cap, but a predictable issuance rate that adjusts based on total stake; EIP-1559 burns the base fee | Validator issuance, indefinitely | Potentially deflationary during high-activity periods — the "ultrasound money" narrative — **but it depends on usage** |

*Computed, not from the source:* at Monero's ~2-minute block time (§1 →
`coin-what-it-is-and-the-three-architectures`), the 0.6 XMR tail emission is 262,800 blocks/year
× 0.6 = **157,680 XMR/year** of perpetual issuance. The source states the per-block rate and
the resulting ~0.87% figure; the annual coin count is arithmetic from the per-block rate and
the block time, and is not a figure the source gives.

### Distribution methods

| Method | How It Works | Pros | Cons |
|---|---|---|---|
| Mining / minting rewards | New coins go to miners/validators who produce blocks | Decentralized distribution; aligns security with distribution | Slow; favors early adopters; ASIC-rich miners may centralize |
| Pre-mine + airdrop | Creator allocates tokens to themselves and distributes some for free | Fast; can fund development; can bootstrap community | Centralization of initial supply; regulatory risk (securities law); credibility concerns |
| Genesis sale / ICO | Tokens sold to early investors before launch | Raises development capital; broad distribution | Securities law exposure (Howey test); many ICOs were scams |
| Proof of airdrop | Tokens distributed to holders of an existing token or users of a protocol | Wide distribution to engaged users | Sybil attacks; may not reach intended recipients |
| Liquidity mining / yield farming | Tokens distributed to users who provide liquidity or use a protocol | Bootstraps usage and liquidity | Attracts mercenary capital that leaves when rewards end |

> **Carry the disclaimer into every one of these.** Three of the five rows — pre-mine + airdrop,
> genesis sale / ICO, and proof of airdrop — distribute or sell tokens to the public, and the
> source names securities-law exposure (the Howey test) on the ICO row and regulatory risk on
> the pre-mine row explicitly. Creating a cryptocurrency is a legitimate software engineering
> exercise with well-documented open-source reference implementations; **deploying one that
> handles real value carries serious legal, financial, and security responsibilities.** Consult
> counsel regarding securities law, AML/KYC requirements, and consumer protection
> regulations in your jurisdiction before launching anything that distributes tokens to the
> public.

### Security budget — the most important economic number

The **security budget** is what it costs to attack the network.

| Consensus | What the attacker must buy | Additional cost |
|---|---|---|
| **PoW** | Enough hashpower to execute a 51% attack — roughly equal to what honest miners earn, because the same hardware could be used for honest mining | — |
| **PoS** | Enough stake to control consensus | Plus the risk of **slashing** if the attack is detectable |

A cryptocurrency with a small security budget is cheap to attack. **This is why small PoW
chains are vulnerable** — the hardware to attack them is inexpensive relative to the potential
gain. The number to watch is not market capitalization; it is what honest block producers are
paid per unit time, because that is the floor on what an attacker must outspend.

### Fee market design

| Model | Mechanism | Properties |
|---|---|---|
| **EIP-1559** (Ethereum's current fee model) | A **base fee** that adjusts with demand — rising when blocks are full, falling when they are not — and is **burned**; users add a **priority fee** (tip) to incentivize inclusion | Makes fees more predictable; creates deflationary pressure |
| **First-price auction** (Bitcoin) | Bidders guess what fee will get them included | Less efficient, but **proven over 17 years** |

The two models are not interchangeable choices of equal weight: the burn in EIP-1559 is what
couples the fee market to supply policy above, so picking a fee model is also picking part of
your issuance model.

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
