---
id: skill-8-economics-and-tokenomics-9d091dddba
purpose: 8 economics and tokenomics
source: src/vibey_tools/skills/plugins/building-a-cryptocurrency/skills/coin-networking-and-tokenomics/SKILL.md
requires: ["skill-7-the-networking-layer-c4802ba0de"]
links: ["skill-where-the-rest-of-the-reference-is-f75b18e9f6"]
---

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
