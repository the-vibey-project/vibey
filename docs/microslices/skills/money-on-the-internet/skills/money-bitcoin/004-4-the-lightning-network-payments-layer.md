---
id: skill-4-the-lightning-network-payments-layer-2d4ceb5891
purpose: 4 the lightning network payments layer
source: src/vibey_tools/skills/plugins/money-on-the-internet/skills/money-bitcoin/SKILL.md
requires: ["skill-3-using-bitcoin-well-aae06dc179"]
links: ["skill-5-mining-economics-in-2026-the-part-nobody-predicts-well-5ab1870986"]
---

## 4. The Lightning Network (payments layer)

**[DURABLE] mechanics**: two parties lock funds into a 2-of-2 on-chain output, then exchange **commitment transactions** off-chain as many times as they like; only open/close/settlement hit the chain. Payments route across channels atomically via **HTLCs** (hash-time-locked contracts) — the whole route settles or nothing does. Watchtowers guard against a counterparty broadcasting an old state while you're offline.

**Where it stood at mid-2026** (treat as a moving target; the sources below are the best current public scoreboards):
- Public capacity **~4,898 BTC across ~41,080 channels / ~17,438 nodes (May 2026)**, down from a **~5,637 BTC ATH in Dec 2025** — capacity has been consolidating toward large, well-connected nodes ([Spark research](https://www.spark.money/research/lightning-network-2026-state)).
- **BOLT 12 "Offers"** (reusable invoices, refunds, recurring payments; merged to spec Sept 2024) is now native in **Core Lightning, LDK and Eclair**; **splicing** (resize a channel without closing it) is production in Core Lightning and central to Eclair/Phoenix, splice-out-capable in LDK — **and LND, the dominant implementation, still lacked both natively as of v0.21.0-beta (June 2026)**, using an LNDK sidecar for offers ([HOGE Wire](https://hoge.gg/lightning-network-bolt12-splicing-lnd-gap/), [Spark implementation comparison](https://www.spark.money/tools/bitcoin-lightning-implementation-comparison)).
  - ⚠️ **Source conflict, reported as found**: [WeeklyReviewer](https://weeklyreviewer.com/dive-deeper/bitcoin-lightning-bolt12-enterprise-payments-2026) claims all four implementations shipped BOLT12 by Q1 2026 incl. LND v0.19.0; three later, more detailed mid-2026 sources say LND still lacks it. The later, specialized sources look more reliable — but verify against LND's release notes before depending on this.
- LDK-based embedded wallets reportedly carry ~25% of LN volume; exchanges (incl. Coinbase, Binance, Kraken) support LN deposits/withdrawals; USDT over Taproot Assets exists on Lightning. Channel-less alternatives (Spark, Ark) and Liquid occupy adjacent niches.
- Persistent pain points, **[DURABLE-ish]**: **inbound liquidity** (you can't receive until someone locks funds *toward* you), offline-receive UX, and watchtower reliance.

Routing fees run ~0.01–0.05% per payment — two orders of magnitude below card rails, which is why LN keeps reappearing in payments discussions despite the UX overhead.

---
