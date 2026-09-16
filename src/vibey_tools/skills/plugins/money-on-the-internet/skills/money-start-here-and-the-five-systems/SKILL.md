---
name: money-start-here-and-the-five-systems
description: "Use when choosing which money rail to study or build on, when you need the five systems (Bitcoin, Ethereum, Monero, PayPal, Stripe) positioned against each other on finality, censorship, programmability, privacy and cost, or when you need to know how durable a claim in this reference is. Start here. Companion to the other money-on-the-internet skills."
---

# Money on the Internet: Start Here

> **Part 1 of 7** of the *Money on the Internet* reference (plugin
> `money-on-the-internet`), covering the pack's method, the five systems positioned, and the learning paths. Sibling skills:
> `money-bitcoin` (§1–§7 — UTXOs, policy vs consensus, wallets, Lightning, mining economics, Core development, the v30 fight),
> `money-ethereum` (§1–§5 — the account model, proof of stake, upgrades, using it, Solidity/Foundry/DeFi/security),
> `money-monero` (§1–§7 — the privacy stack, FCMP++, the Qubic affair, access and delistings, daemon/wallet development),
> `money-paypal` (§1–§6 — what it is, using it, the Sept 2026 US fee schedule, PYUSD, the APIs, PayPal vs Stripe),
> `money-stripe` (§1–§7 — the PaymentIntent model, integration patterns, compliance, pricing, the Bridge/Privy/Tempo stack),
> `money-choosing-a-rail-and-shared-patterns` (§1–§5 — the side-by-side, decision heuristics, the four transferable patterns, a study roadmap, the docs shelf),
> Section numbers are **per skill** here, not shared across the set: each chapter is a
> self-contained system. A reference written as §N → `skill` points at that skill's own §N.
>
> **Currency:** compiled 16 September 2026. This skill is mostly **[DURABLE]** framing; the comparison table carries dated fee and finality figures that expire. The pack's own tagging convention — **[DURABLE]**, **[as of …]**, **[CONTESTED]** — is explained below and used throughout every sibling skill.
>
> **Not investment, legal, tax, or compliance advice.** The regulatory sections tell you what
> to ask your counsel, not what your obligations are.

> **⚠️ Two worlds with incompatible failure modes. Pick which one you are in before anything else.**
>
> **⚠️ GOTCHA** boxes and the pack's **[DURABLE]** / **[as of …]** / **[CONTESTED]** tags mark
> what is safe to learn once and what must be re-verified.
>
> **The three ideas that organize this document:**
> 1. **⚠️ ON THE CRYPTO SIDE, DEPLOYED CODE OR A HELD KEY *IS* MONEY IN PUBLIC**
>    **There is no chargeback and nobody to call. Your failure modes are theft, loss, and protocol risk.**
> 2. **⚠️ ON THE FIAT SIDE, MONEY IS DATA WITH A COUNTERPARTY AND A REGULATOR**
>    **There *is* someone to call — and that someone can freeze you, reverse you, and hold 90-day reserves. Your failure modes are idempotency bugs, webhook mishandling, reconciliation drift, and account risk.**
> 3. **⚠️ DURABILITY IS TAGGED PER CLAIM, NOT PER DOCUMENT**
>    **Learn the [DURABLE] mechanics once. Re-verify every [as of …] claim against its link. Treat [CONTESTED] as genuinely open — both positions are shown with their sources.**

---

**A deep-learning pack: using them, and building on them.**
Compiled 16 September 2026. Dated claims carry source links; volatile numbers carry "as of" anchors. Where sources disagreed, the disagreement is reported rather than smoothed over.

This is an engineering and usage guide. It is **not investment, legal, tax, or compliance advice** — the regulatory sections tell you what to ask your counsel, not what your obligations are.

---

## How this pack was built (and how to trust it)

The durable mechanics (consensus, the EVM, the payment lifecycle, PCI scope, fraud models) come from curated technical references re-verified in August 2026; everything with a shelf life — versions, fees, fork dates, prices, regulation — was searched against primary or near-primary sources **on 16 September 2026**. Three reading rules:

1. **[DURABLE]** mechanics don't expire: UTXO vs account models, the EVM storage layout, idempotency keys, checks-effects-interactions. Learn these once.
2. **[as of …]** claims will expire — a fee schedule, a fork date, a client version. The "as of" tells you when to re-verify, and every one carries a link so you can.
3. **[CONTESTED]** marks genuine disagreement (e.g., whether Qubic ever really had 51% of Monero's hashrate). Where sources conflict, both positions are shown with their sources.

Where a search found nothing, that's stated too. Nothing here is padded out with plausible-sounding reconstruction.

---

## The five systems, positioned

| | **Bitcoin** | **Ethereum** | **Monero** | **PayPal** | **Stripe** |
|---|---|---|---|---|---|
| What it actually is | A settlement asset + PoW ledger | A programmable settlement platform | Privacy-preserving PoW currency | A two-sided account network + PSP | A developer-first PSP/aggregator |
| Native asset | BTC | ETH + the whole token universe | XMR | USD etc. (PYUSD on-chain) | None — moves fiat (and now stablecoins) |
| Who can censor/reverse | Miners (expensively); txs irreversible | Validators; txs irreversible | Miners; txs irreversible | **PayPal can**: freeze, reverse, hold | **Stripe can**: freeze, reserve, terminate |
| Finality | Probabilistic (~6 confs ≈ 1 hr) | ~13 min cryptographic finality | Probabilistic (~10 blocks ≈ 20 min convention) | Instant in-ledger, **days to cash out, months of chargeback tail** | Same fiat rails; payout T+1–T+2 typical |
| Programmability | Limited Script + PSBT/miniscript + Lightning | **Full smart contracts (EVM)** | Essentially none (by design) | REST APIs, Braintree, payouts | The broadest payment API surface |
| Privacy | Pseudonymous, fully public | Pseudonymous, fully public | **Private by default** (sender, receiver, amount) | Fully surveilled, KYC'd | Fully surveilled, KYC'd |
| Headline cost to accept money | On-chain: variable fee market (~sub-$1 typical in 2026's low-fee era but spikes); Lightning: ~0.01–0.05% routing | L1 ~sub-cent–$0.25 typical as of Sep 2026; L2s fractions of a cent | Negligible (cents) | 2.99–3.49% + $0.49 (US online, fee PDF eff. 1 Sep 2026) | 2.9% + $0.30 online cards (US) |
| "Developing on it" means | Node ops, wallets, PSBT/multisig, Lightning, BDK | Smart contracts (Solidity) + clients + L2s + DeFi | Daemon/wallet RPC, view keys, atomic swaps | Orders/Payouts/Subscriptions APIs, Braintree, PYUSD rails | PaymentIntents, Checkout, Connect, Billing, stablecoin stack |

**The one framing that organizes everything:**

- On the crypto side: **deployed code (or a held key) is money in public.** There is no chargeback and no one to call. Your failure modes are theft, loss, and protocol risk.
- On the fiat side: **money is data with an audit trail, a counterparty, and a regulator.** There *is* someone to call — and that someone can also freeze you, reverse you, and hold 90-day reserves. Your failure modes are idempotency bugs, webhook mishandling, reconciliation drift, and account risk.
- Monero sits deliberately at the far end of the crypto side: it buys fungibility and privacy at the price of regulatory exclusion from most regulated on-ramps.

---

## Learning paths depending on what you want

**"I want to accept payments online for a business"** → `money-stripe` first, then `money-paypal`'s fee table, then `money-choosing-a-rail-and-shared-patterns`'s MoR section. The chain skills matter only if your customers want to pay in crypto — and the modern answer there is now *stablecoin acceptance via Stripe/Bridge or PayPal PYUSD*, not self-hosted nodes.

**"I want to become a smart-contract engineer"** → `money-ethereum`, in order: EVM model → Solidity → Foundry testing ladder → the security canon (access control is where the money is lost, per 2026 loss data) → DeFi primitives → MEV.

**"I want to become a protocol engineer"** → `money-bitcoin`'s policy-vs-consensus material (the v30 OP_RETURN fight is the cleanest live lesson in what "decentralized governance" actually means) + `money-ethereum`'s client/upgrades material.

**"I care about privacy / censorship resistance"** → `money-monero` in full, including the Qubic reorg episode and the delisting map — the honest version includes the costs, not just the cryptography.

**"I'm evaluating the agentic/stablecoin payments wave"** → §6 → `money-stripe` (Bridge/Privy/Tempo) + §5 → `money-paypal` (PYUSD/PYUSDx) + §4 → `money-choosing-a-rail-and-shared-patterns`. Note the reality check inside: the flagship agentic checkout product was retired in March 2026 after low adoption (see `money-stripe`).

---

## The rest of the set

- `money-bitcoin` — protocol, wallets, Lightning, mining economics, Bitcoin Core development,
  and the v30 governance fight
- `money-ethereum` — the EVM, proof of stake, upgrades, Solidity and Foundry, DeFi, security
  and ops
- `money-monero` — the privacy stack, FCMP++, the 2025 Qubic episode, delistings, wallet and
  daemon development
- `money-paypal` — the US fee schedule effective 1 Sept 2026, Orders/Braintree/Payouts APIs,
  PYUSD and the agentic strategy
- `money-stripe` — the PaymentIntent model, the API surface, Connect and Billing, and the
  Bridge–Privy–Tempo stablecoin stack
- `money-choosing-a-rail-and-shared-patterns` — the side-by-side, decision heuristics, the four
  transferable engineering patterns, a sequenced study roadmap, and the canonical docs shelf
