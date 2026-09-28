---
id: skill-1-what-it-is-93e2a2ccad
purpose: 1 what it is
source: src/vibey_tools/skills/plugins/money-on-the-internet/skills/money-bitcoin/SKILL.md
requires: []
links: ["skill-2-protocol-mechanics-that-matter-5a07c6ec5c"]
---

## 1. What it is

Bitcoin is a **replicated ledger ordered by proof of work**, with a fixed issuance schedule and no account system — the ledger is a set of **unspent transaction outputs (UTXOs)**, each locked by a small program, and a "balance" is just the sum of UTXOs your keys can unlock. Three consequences drive everything else:

1. **Transactions destroy and create UTXOs** — they fully consume inputs and produce new outputs (payments + your "change" back to yourself). There is no "account balance" to decrement.
2. **Finality is probabilistic.** Each block on top of your transaction raises the cost of rewriting history; "confirmed" means "computationally buried," conventionally treated as settled at ~3–6 confirmations for serious amounts. **[DURABLE]**
3. **Consensus rules vs. mempool policy are different layers** — what nodes will *accept into a block* vs. what they will *relay*. The 2025 Core v30 fight (§7) showed this distinction is the actual constitution of Bitcoin governance.

**[DURABLE]** The monetary rules: block subsidy halves every 210,000 blocks (~4 years); the April 2024 halving set it to **3.125 BTC/block**, with the next halving around mid‑2028 (to 1.5625). Cap ~21M BTC. Difficulty retargets every 2,016 blocks to hold the ~10-minute block interval — it stood at **127.45T after +1.31% on 5 Sept 2026, with ~+5.26% expected 19 Sept** ([Hashrate Index weekly roundup, 14 Sep 2026](https://beta.hashrateindex.com/blog/hashrate-index-roundup-september-14-2026/)).

**As of 16 Sep 2026**, BTC trades around **$75–76K** — well below the **$126,198 all-time high (6 Oct 2025)** — after the US Senate **failed to advance the CLARITY Act (49–50 cloture vote, 15 Sep 2026)** and ~$450M flowed out of US spot ETFs in a day ([Economic Times](https://economictimes.indiatimes.com/markets/cryptocurrency/crypto-news/bitcoin-trades-near-75000-as-clarity-act-setback-weighs-fed-decision-in-focus/articleshow/134285423.cms), [crypto.news](https://crypto.news/bitcoin-ether-longs-lose-380m-after-senate-vote/)). Prices are the most volatile claim in this pack; re-check before use.

---
