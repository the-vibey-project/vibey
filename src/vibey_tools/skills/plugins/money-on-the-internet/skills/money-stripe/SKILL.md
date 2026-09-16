---
name: money-stripe
description: "Use when integrating or evaluating Stripe — the PaymentIntent lifecycle, idempotency and webhooks, integration patterns from Payment Links to full custom, PCI scope, Connect and Billing and Radar and Terminal, US pricing as of September 2026, Managed Payments as merchant-of-record, and the Bridge/Privy/Tempo stablecoin stack. Companion to the other money-on-the-internet skills."
---

# Stripe

> **Part 6 of 7** of the *Money on the Internet* reference (plugin
> `money-on-the-internet`), covering §1–§7. Sibling skills:
> `money-start-here-and-the-five-systems` (how to read the pack, the five systems positioned side by side, learning paths),
> `money-bitcoin` (§1–§7 — UTXOs, policy vs consensus, wallets, Lightning, mining economics, Core development, the v30 fight),
> `money-ethereum` (§1–§5 — the account model, proof of stake, upgrades, using it, Solidity/Foundry/DeFi/security),
> `money-monero` (§1–§7 — the privacy stack, FCMP++, the Qubic affair, access and delistings, daemon/wallet development),
> `money-paypal` (§1–§6 — what it is, using it, the Sept 2026 US fee schedule, PYUSD, the APIs, PayPal vs Stripe),
> `money-choosing-a-rail-and-shared-patterns` (§1–§5 — the side-by-side, decision heuristics, the four transferable patterns, a study roadmap, the docs shelf),
> Section numbers are **per skill** here, not shared across the set: each chapter is a
> self-contained system. A reference written as §N → `skill` points at that skill's own §N.
>
> **Currency:** compiled 16 September 2026. §2 (core API mechanics) is **[DURABLE]**. §5 (pricing) and §7 (regulatory backdrop) are dated, and §6 (the stablecoin stack) is **[VERSIONED, fast-moving]** — including a flagship agentic-checkout product retired in March 2026.
>
> **Not investment, legal, tax, or compliance advice.** The regulatory sections tell you what
> to ask your counsel, not what your obligations are.

> **⚠️ A developer-first aggregator: gateway, processing, and a pooled merchant account, sold as APIs.**
>
> **⚠️ GOTCHA** boxes and the pack's **[DURABLE]** / **[as of …]** / **[CONTESTED]** tags mark
> what is safe to learn once and what must be re-verified.
>
> **The three ideas that organize this document:**
> 1. **⚠️ THE PAYMENTINTENT IS A STATE MACHINE, AND YOUR CODE MUST TREAT IT AS ONE**
>    **Confirm, requires_action, succeeded — with SCA stepping out to the customer and back. Modelling it as a synchronous call is the single most common integration defect.**
> 2. **⚠️ IDEMPOTENCY KEYS AND WEBHOOKS ARE NOT OPTIONAL EXTRAS**
>    **They are the two mechanisms that make money movement safe under retry and partial failure. Every serious incident in this domain traces back to skipping one of them.**
> 3. **⚠️ THE POOLED MERCHANT ACCOUNT IS CONVENIENCE *AND* EXPOSURE**
>    **Onboarding in minutes is the same fact as Stripe being able to freeze, reserve or terminate you. Choose the integration pattern with that in view, not just the API ergonomics.**

---

## 1. What it actually is

Stripe is a **developer-first PSP/aggregator**: gateway + processing + a pooled merchant account under Stripe's, sold through APIs. The 2026 surface: **Payments** (PaymentIntents, Checkout, Payment Links), **Billing** (subscriptions, invoicing, usage/metering), **Connect** (multi-party payments), **Radar** (fraud ML), **Terminal** (in-person), **Issuing** (cards), **Tax**, **Identity/Crypto onboarding**, **Financial Connections**, **Managed Payments** (merchant-of-record, added April 2026), and a **stablecoin stack** (Bridge, Privy, Tempo — §6).

**[DURABLE] The one mental model that pays for itself**: Stripe is a state machine API over the card/bank networks. You are never "charging a card"; you are moving a **PaymentIntent** through `requires_payment_method → requires_confirmation → requires_action (3DS) → processing → succeeded` (or `requires_capture` if auth-only), with **webhooks announcing transitions**. Authorization ≠ capture ≠ settlement ≠ payout — they happen at different times and can fail independently. Fulfil physical goods on **capture**, ideally funded by the webhook, never on a redirect.

---

## 2. Core API mechanics — [DURABLE]

**Idempotency**: every POST accepts an `Idempotency-Key`; Stripe caches the first result 24h and replays it on duplicate keys.
```
✓ key = stable hash of your internal checkout_attempt_id  (persisted BEFORE first call)
✗ key = uuid4() regenerated per retry   // protects nothing
```
**Webhooks**: at-least-once, up to ~72h of retries with backoff; verify signature against the **raw** body; return 200 fast; dedupe on event ID with a unique DB constraint; re-fetch the resource from the API rather than trusting the payload; handle out-of-order delivery; dead-letter repeated failures. One infra event delivered the same `checkout.session.completed` **three times in 60 seconds** in a documented incident — non-idempotent handlers triple-provisioned.
**Errors**: declines (`card_error` with decline codes) vs API errors vs **indeterminate** (timeouts/500s — Stripe's own guidance: treat as unknown, reconcile via webhooks, they attempt to reconcile such requests). Retry 5xx/network with same idempotency key, exponential backoff + jitter, capped. Retry soft declines (per network rules); **never retry hard declines** (stolen/invalid/revoked).
**Money**: integer **minor units** + ISO-4217 currency; JPY/KRW have 0 decimals, BHD/KWD/JOD have 3 — a hardcoded `×100` breaks them. Never float math. Store original amount+currency alongside converted values.
**API versioning**: Stripe pins your account to a dated version; upgrades are deliberate projects. **Current channel: `dahlia` — latest `2026-08-26.dahlia`** (channels: acacia → basil → clover → dahlia). The first dahlia release (`2026-03-25.dahlia`) was **breaking**; monthly versions since are additive ([Stripe changelog](https://docs.stripe.com/changelog), [dahlia notes](https://docs.stripe.com/changelog/dahlia.md)). Highlights this year: UPI support; Checkout card funding-type restrictions; Customer Sessions querying entitlements; subscription item limit 20→100; standardized payment-failure error codes; Metadata on confirmation tokens; crypto payouts on new networks (June: Sui); **Managed Payments (MoR) (April)**; the **preview channel** already carries agentic **Shared Payment Tokens** APIs and a *planned* breaking removal of `payment_method_types` on Intents. Node SDK v22.6.x pins `2026-08-26.dahlia`.

---

## 3. Integration patterns — easiest→most-control

1. **Payment Links** — no code.
2. **Checkout** (hosted page) — the correct default for most: wallets surfaced, SCA handled, lowest PCI exposure.
3. **Payment Element / Elements** (embedded, Stripe.js-hosted fields) — custom UI, card data still never touches your servers.
4. **Raw PaymentIntent API** — full control, full responsibility.

```ts
// server (Node, SDK v22)
const intent = await stripe.paymentIntents.create(
  { amount: 4999, currency: "usd", automatic_payment_methods: { enabled: true },
    metadata: { order_id: "ord_1042" } },
  { idempotencyKey: `pi:create:${order.attemptId}` });
// client: confirm with Payment Element using intent.client_secret; Stripe.js owns the card inputs

// webhook: the ONLY fulfillment trigger
const event = stripe.webhooks.constructEvent(rawBody, sig, WH_SECRET); // raw body, before parsing
if (alreadyProcessed(event.id)) return res.sendStatus(200);
if (event.type === "payment_intent.succeeded") {
  const pi = await stripe.paymentIntents.retrieve(event.data.object.id); // re-fetch
  await db.fulfillIfCaptured(pi.metadata.order_id, pi.id);               // idempotent by pi.id
}
res.sendStatus(200);
```

**Testing**: test mode ≠ production (latency, decline fabric behavior, webhook timing all differ); the **Stripe CLI** (`stripe listen --forward-to`) is the dev-loop essential; **test clocks** simulate Billing time-travel; card `4242…4242` family covers happy/failure/3DS paths; do $1 live smoke tests.

---

## 4. Compliance reality (US/EU, as of 2026)

- **PCI DSS v4.0.1** has been the only active version since **31 Mar 2025**. For e-commerce the load-bearing rules are **6.4.3** (payment-page scripts authorized/inventoried/integrity-checked) and **11.6.1** (weekly tamper detection) — both anti-Magecart. ⚠️ **The SAQ A trap**: in Jan 2025 the PCI SSC removed those from SAQ A but replaced them with an eligibility test — **can you confirm your whole e-commerce site is not susceptible to malicious scripts?** With a redirect/iFrame Checkout flow plus written PSP confirmation you can; otherwise you fall to SAQ A-EP's much larger requirement set. Practical implementation regardless: CSP + SRI, and minimum third-party JS on checkout.
- **SCA/3DS2**: EU/UK two-factor requirement; use PaymentIntents/Checkout and exemptions (MIT, TRA, low-value) flow automatically. PSD3/PSR refines rather than replaces 3DS2 — watch for expanded SCA triggers (new tokens, limit changes) once in force.
- **Authorization rate ≈ hidden revenue**: levers are network tokens, account updater, correct MCC, local acquiring, and full 3DS data. A +1% auth-rate lift typically beats any frontend conversion work — nearly nobody measures it.
- **Fraud/chargebacks**: merchant eats CNP fraud via chargebacks; **friendly fraud** is often the largest bucket; network **ratio monitoring** (not totals) is what gets you terminated — prevention (clear descriptor, easy cancellation, Order Insight-style deflection) beats representment, and **you pay the dispute fee ($15) even when you win**. False positives quietly strangle revenue; measure both sides.

---

## 5. Money movement products & pricing (US, as of Sept 2026)

From [stripe.com/pricing](https://stripe.com/pricing) (headline rows; deeper line-items per [transferfees.io guide](https://transferfees.io/guides/stripe-fees-explained/) / [payoutmath calculator](https://payoutmath.com/stripe-fee-calculator/)):

| Item | Fee |
|---|---|
| Online domestic cards | **2.9% + $0.30** |
| In-person (Terminal) | 2.7% + $0.05 |
| Manually keyed | 3.4% + $0.30 |
| International card / currency conversion | **+1.5% / +1%** |
| ACH Direct Debit | 0.8% (cap $5) — the answer for large B2B invoices |
| **Stablecoin acceptance** | **1.5%** (promo **0.8% through 1 Jan 2027**) |
| Stripe Billing (subscriptions) | +0.5–0.7% of recurring |
| Invoicing | 0.4–0.5% of paid invoices |
| Disputes | $15 (received) + $15 if countered |
| Instant Payouts | 1.5% (min $0.50); standard payouts free |
| BNPL (Klarna/Affirm, US/CA) | 5.99% + $0.30 |

Product notes: **Connect** (Express/Standard/Custom) is the standard answer for marketplaces — building payouts/KYC/licensing yourself means money-transmitter licenses (US state-by-state) — you still own split logic, negative-balance policy, 1099-K/DAC7 reporting. ⚠️ **Decide explicitly who bears chargebacks — platform or seller — and build the ledger to reflect it.** **Billing**: dunning + account updater + smart retries target **involuntary churn**, usually the largest, most fixable churn source; proration policy is a documented design decision, not an accident; usage billing needs idempotent usage records. **Managed Payments (April 2026)** makes Stripe itself the merchant of record for tax/compliance — now a serious alternative to Paddle-style MoRs for digital goods sold globally.

---

## 6. The stablecoin stack: Bridge + Privy + Tempo — [VERSIONED, fast-moving]

- **Bridge** — stablecoin orchestration/issuance; **acquired for $1.1B (announced Oct 2024)**. Its **Open Issuance** platform (Oct 2025) powers custom stablecoins incl. MetaMask, Phantom, Hyperliquid's USDH, Sui's USDsui. **Feb 2026: OCC granted Bridge a conditional national trust bank charter** (Circle, Ripple and Paxos in the same cohort) toward federal stablecoin issuance/custody/reserve management ([GL Insight](https://www.glinsight.com/stripes-vertical-stablecoin-stack-bridge-tempo-and-a-1-5-take-rate/)).
- **Privy** — embedded-wallet infrastructure (custodial key management inside apps; Ramp's stablecoin accounts are custodied via Privy).
- **Tempo** — the payments-first blockchain Stripe co-developed with Paradigm. **Mainnet live March 2026**: EVM-compatible L1, sub-second finality, stablecoin-denominated fees (~$0.001 fixed), **no native token**. Validators include Visa, Stripe, Zodia Custody, MoneyGram; design partners: Mastercard, Deutsche Bank, Revolut, Nubank, Shopify, OpenAI, Anthropic ([Tempo blog](https://tempo.xyz/blog/stripe-and-tempo-stablecoin-settlement-for-global-money-movement/)).
- **April 2026**: Stripe's money-management APIs support stablecoin transfers on Tempo; businesses in 100+ countries can hold/send/receive stablecoins from Stripe — expanding into Connect payouts, Issuing and onramps.
- **Flagship customers**: **Deel** (June 2026) — contractor wallet for 1.5M contractors/150+ countries on the full stack (Bridge Open Issuance stablecoin DLUSD + Privy wallets + Tempo settlement; live in Argentina first) ([Stripe newsroom](https://stripe.com/newsroom/news/deel-and-stripe)); **Ramp** — stablecoin accounts + bill pay with up to 3.25% rewards on balances ([The Defiant](https://thedefiant.io/converge/tradfi-and-fintech/ramp-adds-stablecoin-accounts-and-bill-pay-on-stripe-stack)).
- **Economics**: 1.5% merchant take rate on near-zero settlement cost — an "interchange-shaped" margin opportunity at the PSP layer; competitive pressure from Circle's Arc and Mastercard's BVNK acquisition. Treat pricing as promo-fragile: the **0.8% promo ends 1 Jan 2027**.
- **Agentic payments**: Stripe co-authored **ACP** with OpenAI (Sept 2025) and launched **MPP** (agent pre-authorizes a spend limit, streams micropayments, Mar 2026); Shared Payment Tokens sit in the current preview API (§2). ⚠️ **Reality check**: OpenAI's Instant Checkout — the ACP flagship — was **retired 5 Mar 2026** after ~30 merchant integrations, and consumer adoption stayed low through its life. Build machine-readable catalogs and adopt a standard (don't roll your own agent-payment flow — that's how you inherit the fraud liability), but don't bet the roadmap on agent volume yet.

---

## 7. Regulatory backdrop that touches Stripe builders — [as of 16 Sep 2026]

**GENIUS Act** (US payment-stablecoin law, signed 18 Jul 2025): regulators **missed the 18 Jul 2026 rulemaking deadline**; Treasury's NPRM (proposed 12 CFR Part 1523, covering issuance/offer/sale prohibitions and the Section 18 foreign-issuer comparability regime) was published **18 Aug 2026**, comments close **19 Oct 2026**; a joint FinCEN/OCC/Fed/FDIC/NCUA NPRM (22 Jun 2026) would treat permitted issuers as **BSA financial institutions** with customer-identification duties. **The enforcement date — 18 Jan 2027 — is fixed by statute** and doesn't move with the rulemaking slippage; OCC committed to final rules by Nov 2026. Penalties: up to $1M + 5 years criminal for knowing violations; ~$100K/day civil for domestic issuers ([Federal Register, 18 Aug 2026](https://www.federalregister.gov/documents/2026/08/18/2026-16796/genius-act-regulations-on-payment-stablecoin-issuance-offer-and-sale), [joint BSA NPRM](https://www.federalregister.gov/documents/full_text/html/2026/06/22/2026-12460.html), [Forkast on the compliance cliff](https://forkast.news/the-genius-act-compliance-cliff-137-days-to-a-deadline-without-rules/), [Astraea Counsel roadmap](https://astraea.law/insights/genius-act-stablecoin-compliance-roadmap)). Charters so far: Circle (final, Jul 2026); conditional: Bridge, Ripple, BitGo, Fidelity, Paxos.
**Market-structure (CLARITY Act)**: cloture **failed 49–50 in the Senate on 15 Sep 2026**, ending 2026 passage odds — the proximate cause of that week's crypto selloff ([crypto.news](https://crypto.news/bitcoin-ether-longs-lose-380m-after-senate-vote/)).
**MiCA (EU)**: fully applicable to CASPs; the Sept 2026 searches surfaced no new MiCA developments (reported as found), while the US Treasury NPRM's comparability question explicitly tees up whether MiCA counts as "equivalent" for foreign issuers — that's the transatlantic thread to watch into 2027.

---

## Sources (as of 16 Sep 2026)

[Stripe pricing](https://stripe.com/pricing) · [Stripe API changelog / dahlia](https://docs.stripe.com/changelog) · [Tempo × Stripe](https://tempo.xyz/blog/stripe-and-tempo-stablecoin-settlement-for-global-money-movement/) · [GL Insight: the vertical stack](https://www.glinsight.com/stripes-vertical-stablecoin-stack-bridge-tempo-and-a-1-5-take-rate/) · [Stripe/Deel newsroom](https://stripe.com/newsroom/news/deel-and-stripe) · [The Defiant: Ramp](https://thedefiant.io/converge/tradfi-and-fintech/ramp-adds-stablecoin-accounts-and-bill-pay-on-stripe-stack) · [Federal Register GENIUS NPRM](https://www.federalregister.gov/documents/2026/08/18/2026-16796/genius-act-regulations-on-payment-stablecoin-issuance-offer-and-sale) · [Forkast](https://forkast.news/the-genius-act-compliance-cliff-137-days-to-a-deadline-without-rules/) · [crypto.news CLARITY vote](https://crypto.news/bitcoin-ether-longs-lose-380m-after-senate-vote/) · fee breakdowns: [transferfees.io](https://transferfees.io/guides/stripe-fees-explained/), [payoutmath](https://payoutmath.com/stripe-fee-calculator/). Payment-lifecycle, PCI, fraud and billing mechanics per the `ecommerce-development` reference set, verified Aug 2026.

Canonical study docs: docs.stripe.com (the Payments lifecycle, webhooks guide, and Connect integration guides are the best-written of any PSP), the Stripe CLI docs, Stripe's engineering blog (idempotency and online-migration posts are classics), and the PCI SSC resource library.
