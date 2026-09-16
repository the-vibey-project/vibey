---
name: money-bitcoin
description: "Use when working with Bitcoin — the UTXO model, policy versus consensus rules, fee estimation and RBF, wallet and key management, multisig and PSBT and miniscript, the Lightning Network, 2026 mining economics, Bitcoin Core and BDK development, or the governance lesson of the v30 OP_RETURN fight. Companion to the other money-on-the-internet skills."
---

# Bitcoin

> **Part 2 of 7** of the *Money on the Internet* reference (plugin
> `money-on-the-internet`), covering §1–§7. Sibling skills:
> `money-start-here-and-the-five-systems` (how to read the pack, the five systems positioned side by side, learning paths),
> `money-ethereum` (§1–§5 — the account model, proof of stake, upgrades, using it, Solidity/Foundry/DeFi/security),
> `money-monero` (§1–§7 — the privacy stack, FCMP++, the Qubic affair, access and delistings, daemon/wallet development),
> `money-paypal` (§1–§6 — what it is, using it, the Sept 2026 US fee schedule, PYUSD, the APIs, PayPal vs Stripe),
> `money-stripe` (§1–§7 — the PaymentIntent model, integration patterns, compliance, pricing, the Bridge/Privy/Tempo stack),
> `money-choosing-a-rail-and-shared-patterns` (§1–§5 — the side-by-side, decision heuristics, the four transferable patterns, a study roadmap, the docs shelf),
> Section numbers are **per skill** here, not shared across the set: each chapter is a
> self-contained system. A reference written as §N → `skill` points at that skill's own §N.
>
> **Currency:** compiled 16 September 2026. The UTXO model, policy-vs-consensus and PSBT mechanics are **[DURABLE]**. Fee levels, client versions, mining economics and the v30 governance outcome are dated — §7 is explicitly **[CONTESTED]**.
>
> **Not investment, legal, tax, or compliance advice.** The regulatory sections tell you what
> to ask your counsel, not what your obligations are.

> **⚠️ A replicated ledger ordered by proof of work, with no accounts — only unspent outputs locked by small programs.**
>
> **⚠️ GOTCHA** boxes and the pack's **[DURABLE]** / **[as of …]** / **[CONTESTED]** tags mark
> what is safe to learn once and what must be re-verified.
>
> **The three ideas that organize this document:**
> 1. **⚠️ THERE ARE NO BALANCES, ONLY UTXOs**
>    **A "balance" is the sum of outputs your keys can unlock. Coin selection, change, fee estimation and privacy leakage all follow from that one fact.**
> 2. **⚠️ POLICY IS NOT CONSENSUS**
>    **What a node will *relay* and what the network will *accept* are different rule sets. Confusing them is what made the v30 fight look like a protocol change when it was a default-policy change — and it is the cleanest live lesson in what decentralized governance actually means.**
> 3. **⚠️ IRREVERSIBILITY IS THE PRODUCT AND THE HAZARD**
>    **Six confirmations is a probabilistic convention, not a guarantee, and there is no reversal path afterwards. Every operational control has to sit *before* broadcast.**

---

## 1. What it is

Bitcoin is a **replicated ledger ordered by proof of work**, with a fixed issuance schedule and no account system — the ledger is a set of **unspent transaction outputs (UTXOs)**, each locked by a small program, and a "balance" is just the sum of UTXOs your keys can unlock. Three consequences drive everything else:

1. **Transactions destroy and create UTXOs** — they fully consume inputs and produce new outputs (payments + your "change" back to yourself). There is no "account balance" to decrement.
2. **Finality is probabilistic.** Each block on top of your transaction raises the cost of rewriting history; "confirmed" means "computationally buried," conventionally treated as settled at ~3–6 confirmations for serious amounts. **[DURABLE]**
3. **Consensus rules vs. mempool policy are different layers** — what nodes will *accept into a block* vs. what they will *relay*. The 2025 Core v30 fight (§7) showed this distinction is the actual constitution of Bitcoin governance.

**[DURABLE]** The monetary rules: block subsidy halves every 210,000 blocks (~4 years); the April 2024 halving set it to **3.125 BTC/block**, with the next halving around mid‑2028 (to 1.5625). Cap ~21M BTC. Difficulty retargets every 2,016 blocks to hold the ~10-minute block interval — it stood at **127.45T after +1.31% on 5 Sept 2026, with ~+5.26% expected 19 Sept** ([Hashrate Index weekly roundup, 14 Sep 2026](https://beta.hashrateindex.com/blog/hashrate-index-roundup-september-14-2026/)).

**As of 16 Sep 2026**, BTC trades around **$75–76K** — well below the **$126,198 all-time high (6 Oct 2025)** — after the US Senate **failed to advance the CLARITY Act (49–50 cloture vote, 15 Sep 2026)** and ~$450M flowed out of US spot ETFs in a day ([Economic Times](https://economictimes.indiatimes.com/markets/cryptocurrency/crypto-news/bitcoin-trades-near-75000-as-clarity-act-setback-weighs-fed-decision-in-focus/articleshow/134285423.cms), [crypto.news](https://crypto.news/bitcoin-ether-longs-lose-380m-after-senate-vote/)). Prices are the most volatile claim in this pack; re-check before use.

---

## 2. Protocol mechanics that matter

**[DURABLE]** Throughout.

- **Mining = Sybil-resistant leader election.** Miners grind SHA-256d over block headers to find a hash under the difficulty target; each block commits to a Merkle tree of transactions. Energy expenditure — not identity — is what makes rewriting history expensive.
- **Script.** Each output carries a locking script; spending provides an unlocking script. Bitcoin Script is intentionally not Turing-complete (no loops). Everything you know — multisig, timelocks (`OP_CHECKLOCKTIMEVERIFY`/`OP_CHECKSEQUENCEVERIFY`), HTLCs for Lightning — is built from this small vocabulary.
- **SegWit (2017, BIP-141)** moved signatures ("witnesses") out of the base block, fixing transaction malleability and enabling both Lightning and the modern address formats. **Taproot (Nov 2021, BIP-340/341/342)** replaced ECDSA with Schnorr signatures (linear, aggregatable, enabling MuSig2) and committed scripts into a Merkle tree (MAST) so that the common key-spend path looks identical to a plain payment — a privacy and efficiency win.
- **Address types** you'll handle as a developer: legacy Base58 (`1…` P2PKH, `3…` P2SH), **bech32 SegWit v0 (`bc1q…`)**, **bech32m Taproot v1 (`bc1p…`)**. **[⚠️ bech32 (BIP-173) has a length-extension weakness; it's only correct for v0. Use bech32m (BIP-350) for anything else.]**
- **Fee machinery**: RBF (BIP-125, opt-in replace-by-fee), CPFP (child-pays-for-parent), **TRUC "v3" transactions (BIP-431)** constraining replacement topology, and package relay. As of Core 31 (§6) the ancestor/descendant model was replaced by **cluster mempool** — if you build fee-bumping tooling, that release is your new reference point.
- **Sighash flags** (`SIGHASH_ALL` etc.) define what a signature commits to; Taproot's `SIGHASH_DEFAULT` is now the common case.
- **Silent Payments (BIP-352)** — reusable static payment codes where the sender derives a fresh on-chain address without any interaction; receiving wallets must scan with their private key, which is the adoption cost.

---

## 3. Using Bitcoin well

**Custody is the whole game.** Key management standards you'll meet everywhere, **[DURABLE]**:
- **BIP-39** seed phrases (human-readable backup; the passphrase option is a plausible-deniability/decoy layer, and a loss vector).
- **BIP-32** hierarchical-deterministic derivation; **BIP-44/49/84/86** account/purpose paths by script type.
- **Descriptors (BIP-380s family)** — strings like `wpkh(xpub…/0/*)` that fully describe a wallet's script structure; the modern interchange format between Core and signing devices.
- **PSBT (BIP-174)** — partially signed transactions passed between coordinator and signers; the backbone of multisig, coinjoin, hardware-wallet and Lightning-splice workflows.

Practical usage rules:
- Verify receive addresses **on the signing device's screen**, not on a potentially compromised host.
- Multisig of 2-of-3 across vendors/geographies is the standard for serious holdings; coordinate it with descriptors + PSBTs, and store the descriptor with each seed (a seed without its derivation path/script info can be an unrecoverable lockbox).
- **[⚠️ Address reuse damages your privacy permanently]** — the ledger is public forever; every serious wallet rotates addresses. Silent Payments (above) are the emerging answer for published donation-style codes.
- Confirmation targets: 1 conf is fine for retail-sized amounts; 3–6 for meaningful value; **be suspicious of 0-conf acceptance from strangers** — RBF exists, and 0-conf is a promise, not a payment.
- Regulated access: US spot Bitcoin ETFs (live since Jan 2024) made brokerage-account exposure routine — with all the tradeoffs of custodial IOUs (you hold a fund share, not keys; Sept 2026's $450M single-day ETF outflow is a reminder that this channel amplifies sentiment swings).

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

## 5. Mining economics in 2026 — the part nobody predicts well

- Network hashrate **flirted with 1 zettahash/s at the start of Sept 2026** (~974 EH/s on 1 Sept; briefly >1.03 ZH/s on 31 Aug), settling to a **~943 EH/s 7-day average mid-month** ([Hashrate Index](https://beta.hashrateindex.com/blog/hashrate-index-roundup-september-14-2026/), [Gate News](https://www.gate.com/news/detail/bitcoin-hashrate-nears-1-zhs-as-mining-profitability-declines-23924973)).
- ⚠️ **Sources disagree on the all-time peak**: CoinWarz records **1.44 ZH/s (20 Sept 2025)**; Maketo cites **1,149 EH/s (18 Oct 2025)**. Different estimators measure differently (hashrate is *inferred* from block times and difficulty, never directly observed). Treat peak claims ±30%.
- Hashprice (revenue per unit of hashrate) fell to the **low-$30s to ~$39 per PH/s/day** in Q3 2026 with BTC ~50% below its 2025 high, squeezing marginal miners off; public miners announced **>$70B in AI/HPC datacenter pivots** (IREN decommissioning Bitcoin hardware; MARA/Riot reallocating power) ([Hashrate Index Q3 heatmap](https://hashrateindex.com/blog/global-hashrate-heatmap-update-q3-2026/)).
- **[DURABLE] lesson**: mining margin = (BTC price × subsidy + fees) − (energy × hashrate growth). It mean-reverts brutally; hardware bought at euphoric hashprice rarely pays back. Stratum V2 (miners construct their own templates) is the decentralization-relevant pool upgrade to track.

---

## 6. Developing on Bitcoin

### 6.1 The stack

| Layer | Tools |
|---|---|
| Node | **Bitcoin Core** (`bitcoind` + JSON-RPC + wallet), Electrum servers, self-hosted **Esplora/mempool.space** for indexing |
| Networks for dev | **regtest** (local, mine instantly), **signet** (stable global testnet), **testnet4** (BIP-94's fix for testnet3's difficulty exploits) |
| Wallets/keys (Rust) | **BDK** (Bitcoin Dev Kit): descriptors, PSBT, coin selection, Electrum/Esplora backends |
| JS/TS | **bitcoinjs-lib** (+ tiny-secp256k1), scure-btc-signer |
| Lightning | **LDK** (library), **Core Lightning** (plugin-centric), **LND** (gRPC), Eclair |
| Crypto core | **libsecp256k1** (the consensus-critical library) |

### 6.2 Bitcoin Core versions you should know about

- **v30.0 (7 Oct 2025)** — the controversial one: default `-datacarriersize` went **83 → 100,000 bytes** (effectively uncapped within tx-size limits), multiple `OP_RETURN` outputs per tx now relay, minrelay fee floor cut to **0.1 sat/vB**. **Zero consensus changes — pure policy** ([release notes](https://bitcoincore.org/en/releases/30.0/), [GitHub notes](https://github.com/bitcoin/bitcoin/blob/master/doc/release-notes/release-notes-30.0.md)).
- **v31.0 (19 Apr 2026)** — **cluster mempool** replaced ancestor/descendant accounting (cluster limits: **64 txs / 101 kB**), RBF accepted only if it strictly improves the mempool **feerate diagram**, **CPFP carve-out removed** (use TRUC + sibling eviction), new RPCs `getmempoolcluster` / `getmempoolfeeratediagram`, `-privatebroadcast` (broadcast only over Tor/I2P), `-dbcache` default 450 MiB → **1024 MiB**, fee-estimator floor 0.1 sat/vB, new REST `/rest/blockpart/` ([bitcoin.org 31.0](https://bitcoin.org/en/releases/31.0/), [announcement](https://bitcoincore.org/en/2026/04/19/release-31.0/)).

**If you operate fee-bumping, CPFP, or any mempool-sensitive logic, read the v31 release notes before anything else in this file.** The pre-31 mental model (25-descendant rule etc.) is gone.

### 6.3 The core workflows, with real commands

```bash
# spin up a private chain
bitcoind -regtest -daemon
bitcoin-cli -regtest createwallet "dev"          # descriptor wallet by default
bitcoin-cli -regtest -generate 101               # past coinbase maturity
# inspect the new cluster mempool on a real node (v31+)
bitcoin-cli getmempoolcluster <txid>
bitcoin-cli getmempoolfeeratediagram
```

```python
# Minimal BDK-style flow (Rust; API sketch, pinned to bdk_wallet 2.x semantics)
// 1. Describe the wallet as a descriptor, not keys-in-code
let external = "wpkh(tprv8.../84'/1'/0'/0/*)";
// 2. Build a tx: add recipient, set feerate, enable RBF
// 3. Sign with the wallet's signer set  4. Broadcast via Esplora/Electrum backend
// Everything about change, UTXO selection, and PSBT export is explicit.
```

**The PSBT/multisig workflow** — the one every Bitcoin dev eventually builds: coordinator creates an *unsigned* PSBT from selected UTXOs → each signer signs offline → coordinator combines → finalize → broadcast. Same pattern powers hardware wallets, coinjoin, and Lightning splices.

### 6.4 Bitcoin-dev gotchas

- **[⚠️ Never put keys or seeds in code, env files in git, or CI logs]** — treat libsecp256k1/HSM/KMS boundaries as load-bearing.
- **Fee estimation**: the mempool can fill between broadcast and block; always build with RBF enabled unless you have a reason not to, and know how to CPFP out of a stuck parent (post-31: TRUC rules apply).
- **Descriptor wallet ≠ legacy wallet**: Core dropped legacy wallet creation; use descriptors and `importdescriptors` for watch-only.
- **Verify PSBT fields before signing** — fee, outputs, and derivation paths — on an airgapped or screened device; blind-signing PSBTs is how multisigs get drained.
- **Test against signet before touching real funds; test reorg handling** (`listtransactions` categories change) — indexers that assume no reorgs will lie to you.
- **[DURABLE] timelock foot‑guns**: relative (BIP-68) vs absolute (BIP-65), nSequence semantics — get these wrong and funds are locked or instantly spendable, with no appeal.

---

## 7. Governance: what the v30 fight taught (2025) — [CONTESTED]

Core v30's OP_RETURN default change produced the sharpest governance clash since the block-size wars: **Bitcoin Knots' node share jumped ~2% → ~20%** as operators rejected the defaults; Luke Dashjr called it "malicious code"; Nick Szabo reappeared to warn of operator legal exposure ([Yellow.com roundup, 1 Oct 2025](https://yellow.com/research/bitcoin-core-v30-release-guide-opreturn-changes-wallet-updates-and-network-impact)). Pieter Wuille's counter-argument ([Bitcoin StackExchange](https://bitcoin.stackexchange.com/questions/127895/implications-of-op-return-changes-in-upcoming-bitcoin-core-version-30-0)): miners already accept large data out-of-band, so restrictive *relay* policy only pushes traffic to private miner APIs — which **centralizes mining** while failing to stop the data.

**[DURABLE] takeaway**: Bitcoin "governance" is rough consensus among independent node operators running whatever policy they choose; consensus rules change only by slow soft-fork activation; policy changes can split the *mempool* without splitting the *chain*. That split-brain is a feature — and the v30/v31 era is your live case study.

---

## Sources (as of 16 Sep 2026)

Bitcoin Core [v30.0 release notes](https://bitcoincore.org/en/releases/30.0/) · [v31.0 release notes](https://bitcoin.org/en/releases/31.0/) · [Hashrate Index weekly, 14 Sep 2026](https://beta.hashrateindex.com/blog/hashrate-index-roundup-september-14-2026/) · [Q3 2026 hashrate heatmap](https://hashrateindex.com/blog/global-hashrate-heatmap-update-q3-2026/) · [CoinWarz hashrate chart](https://www.coinwarz.com/bitcoin-hashrate) · [Maketo hashrate](https://maketo.com/bitcoin/hashrate) · [Spark: LN 2026 state](https://www.spark.money/research/lightning-network-2026-state) · [HOGE Wire: BOLT12/splicing rollout](https://hoge.gg/lightning-network-bolt12-splicing-lnd-gap/) · [Spark: splicing explainer](https://www.spark.money/research/splicing-lightning-channels) · [Spark: implementation matrix](https://www.spark.money/tools/bitcoin-lightning-implementation-comparison) · [WeeklyReviewer (conflicting LND claim)](https://weeklyreviewer.com/dive-deeper/bitcoin-lightning-bolt12-enterprise-payments-2026) · [WT — Wuille on OP_RETURN](https://bitcoin.stackexchange.com/questions/127895/implications-of-op-return-changes-in-upcoming-bitcoin-core-version-30-0) · [Yellow.com v30 guide](https://yellow.com/research/bitcoin-core-v30-release-guide-opreturn-changes-wallet-updates-and-network-impact) · price context: [Economic Times, 16 Sep 2026](https://economictimes.indiatimes.com/markets/cryptocurrency/crypto-news/bitcoin-trades-near-75000-as-clarity-act-setback-weighs-fed-decision-in-focus/articleshow/134285423.cms), [crypto.news](https://crypto.news/bitcoin-ether-longs-lose-380m-after-senate-vote/)

Canonical study docs: the BIPs repo (bips.dev), *Mastering Bitcoin* (3rd ed., Antonopoulos & Harding), Bitcoin Core docs, the Bitcoin Optech newsletter archive (the best week-by-week record of how this ecosystem actually evolves).
