---
id: skill-1-the-mental-model-c002de618f
purpose: 1 the mental model
source: src/vibey_tools/skills/plugins/money-on-the-internet/skills/money-ethereum/SKILL.md
requires: []
links: ["skill-2-proof-of-stake-and-the-two-process-node-durable-5419876112"]
---

## 1. The mental model

Ethereum is Bitcoin's ledger idea generalized into a **world computer**: a replicated state machine where the state includes **accounts with executable code**. Where Bitcoin stores UTXOs, Ethereum stores an **account tree** — externally owned accounts (EOAs, controlled by keys) and **contract accounts** (controlled by their own code). A transaction is either a value transfer or a function call into a contract; every full node re-executes every transaction and must reach the same resulting state.

Three consequences:
- **Composability**: contracts call contracts within a single atomic transaction. This powers DeFi — and means your protocol's safety depends on code you don't control.
- **Everything is public and adversarial**: every function is callable by anyone, in any order, by attackers who read your source. There is no "hidden" on-chain.
- **Bugs are irreversible money losses**; there is no support line. (For reversibility, see PayPal/Stripe — that's the trade.)

**As of 16 Sep 2026**, ETH trades near **$2,400–2,500**, vs an ATH of **$4,953 (24 Aug 2025)**; the Sept 15–16 drawdown tracked Bitcoin's on the failed CLARITY cloture vote ([Economic Times](https://economictimes.indiatimes.com/markets/cryptocurrency/crypto-news/bitcoin-trades-near-75000-as-clarity-act-setback-weighs-fed-decision-in-focus/articleshow/134285423.cms)). Spot ETH ETFs exist (they saw ~$141M outflows on Sept 15).

---
