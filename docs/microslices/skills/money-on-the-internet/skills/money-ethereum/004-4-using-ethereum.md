---
id: skill-4-using-ethereum-cec8448ef7
purpose: 4 using ethereum
source: src/vibey_tools/skills/plugins/money-on-the-internet/skills/money-ethereum/SKILL.md
requires: ["skill-3-upgrades-what-s-shipped-what-s-next-heavily-dated-ee59412b9e"]
links: ["skill-5-developing-on-ethereum-8b99c151b8"]
---

## 4. Using Ethereum

- **Wallets**: EOAs (MetaMask, Rabby, hardware) and **smart accounts** (Safe, ERC-4337 accounts). Since Pectra's **EIP-7702**, an ordinary EOA can temporarily execute as smart-contract code — giving *existing* wallets batching, session keys, sponsored gas, and social recovery without address migration. ⚠️ **7702 is also a drainer vector**: an EOA delegating to malicious code is now a standard phishing payload; never sign a delegation you don't understand, and note that "no code at `msg.sender` ⇒ plain EOA" is no longer a safe assumption in contract logic.
- **L2s are where the activity is**: optimistic rollups (OP Stack, Arbitrum — ~7-day withdrawal windows unless fast-exit) vs. ZK/validity rollups (proof-verified exits in minutes) vs. validiums (cheaper, weaker data availability). **[DURABLE] The only three security questions about any L2**: who can censor you, who can steal from you, and can you exit without permission? **L2Beat's stage classification** answers them honestly; the escape hatch to verify is **forced inclusion via L1**. Most rollups still run a **centralized sequencer** (censorship/liveness SPOF) — decentralized sequencing remains largely unshipped.
- **Bridges are the most-exploited category in crypto history** — lock-and-mint honey pots, and verification of foreign-chain state. Ask of any bridge: *who attests the source-chain event?* A 5-of-9 multisig bridge has the security of a 5-of-9 multisig. A 2026 example: forged Axelar messages passed a receiver contract missing access control → ~$3M drained. Prefer canonical/L1-verified or light-client bridges for size.
- **DeFi essentials**: AMMs (`x·y=k` constant product; concentrated liquidity; LPs bear impermanent loss), over-collateralized lending with liquidation incentives, fiat-backed vs crypto-backed vs algorithmic stablecoins (the last has a long failure history), liquid staking. Oracles: **never read a DEX spot price on-chain as "the price"** — a flash loan moves it in one transaction; use Chainlink/Pyth/RedStone feeds or meaningful TWAPs, and check feed staleness and L2 sequencer uptime.

---
