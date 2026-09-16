---
name: money-paypal
description: "Use when integrating or evaluating PayPal — the consumer network, Braintree and Venmo acceptance, the US merchant fee schedule effective 1 September 2026, PYUSD and the 2026 crypto strategy, the Orders/Payouts/Subscriptions APIs and webhook handling, and when to choose PayPal, Stripe, or both. Companion to the other money-on-the-internet skills."
---

# PayPal

> **Part 5 of 7** of the *Money on the Internet* reference (plugin
> `money-on-the-internet`), covering §1–§6. Sibling skills:
> `money-start-here-and-the-five-systems` (how to read the pack, the five systems positioned side by side, learning paths),
> `money-bitcoin` (§1–§7 — UTXOs, policy vs consensus, wallets, Lightning, mining economics, Core development, the v30 fight),
> `money-ethereum` (§1–§5 — the account model, proof of stake, upgrades, using it, Solidity/Foundry/DeFi/security),
> `money-monero` (§1–§7 — the privacy stack, FCMP++, the Qubic affair, access and delistings, daemon/wallet development),
> `money-stripe` (§1–§7 — the PaymentIntent model, integration patterns, compliance, pricing, the Bridge/Privy/Tempo stack),
> `money-choosing-a-rail-and-shared-patterns` (§1–§5 — the side-by-side, decision heuristics, the four transferable patterns, a study roadmap, the docs shelf),
> Section numbers are **per skill** here, not shared across the set: each chapter is a
> self-contained system. A reference written as §N → `skill` points at that skill's own §N.
>
> **Currency:** compiled 16 September 2026. API mechanics are reasonably durable. **§3's fee schedule is dated to the 1 September 2026 effective date** and §4 (PYUSD) is **[VERSIONED]** — both expire, and both carry source links.
>
> **Not investment, legal, tax, or compliance advice.** The regulatory sections tell you what
> to ask your counsel, not what your obligations are.

> **⚠️ Three things stacked: a consumer account network, a merchant PSP, and — since 2023 — a stablecoin issuer.**
>
> **⚠️ GOTCHA** boxes and the pack's **[DURABLE]** / **[as of …]** / **[CONTESTED]** tags mark
> what is safe to learn once and what must be re-verified.
>
> **The three ideas that organize this document:**
> 1. **⚠️ THE ACCOUNT NETWORK IS THE PRODUCT**
>    **Hundreds of millions of funded consumer accounts is the asset Stripe does not have. That is what you are buying, and what justifies the fee differential.**
> 2. **⚠️ PAYPAL CAN FREEZE, REVERSE AND HOLD**
>    **Unlike a chain, there is someone to call — and that someone is also the party who can put a 90-day reserve on your funds. Account risk is a first-class engineering concern, not a footnote.**
> 3. **⚠️ THE CHARGEBACK TAIL IS MONTHS LONG**
>    **In-ledger settlement is instant; cashing out takes days; dispute exposure runs for months. Reconciliation has to model all three clocks separately.**

---

## 1. What it actually is

PayPal is three things stacked: a **consumer account network** (~hundreds of millions of accounts; Q2 2026 total payment volume **$486.4B, +10% YoY**, net revenue $8.68B — [Cryptonomist on Q2 2026](https://en.cryptonomist.ch/2026/08/03/paypal-pyusd-expansion/)), a **merchant PSP/gateway** (PayPal Checkout, plus **Braintree** for full-stack card processing and **Venmo** acceptance), and — since 2023 — a **stablecoin issuer** (PYUSD). In 2026 PayPal formally combined PYUSD with Braintree merchant processing into a single **"Payment Services & Crypto" division**.

The structural fact that separates PayPal (and Stripe) from everything in the chain skills (`money-bitcoin`, `money-ethereum`, `money-monero`): **PayPal operates entirely inside the regulated banking system, and is itself the counterparty that can reverse, hold, and freeze.** That's what makes it usable for mainstream commerce — buyer protection, chargebacks, fiat settlement — and also what makes account risk (§4) a design input rather than an edge case.

---

## 2. Using it

**As a consumer**: PayPal balance/bank/card funding; **Purchase Protection** with a formal dispute→claim ladder; Pay Later (Pay in 4 / monthly); Venmo for US P2P. From a "how money actually moves" view: your "instant" PayPal payment is a ledger entry *inside PayPal*; the underlying movement is ACH/card settlement days behind it.

**As a merchant**: the value props are (a) **conversion** — PayPal/Venmo buttons skip the card form and inherit stored credentials; (b) cross-border familiarity; (c) Seller Protection *if* you meet its conditions (ship to the verified address, proof of shipment/delivery, eligible categories). The counterweights: fees above headline card rates, dispute exposure, and **account holds/reserves** — which at PayPal are common enough to plan around (see gotchas).

---

## 3. US merchant fees, official schedule effective 1 Sep 2026

From PayPal's own published PDF ([fee schedule, 1 Sep 2026](https://www.paypalobjects.com/marketing/ua/pdf/US/us-merchant-fees-01-september-2026.pdf); [business fees page](https://www.paypal.com/us/business/fees)):

| Flow | Fee |
|---|---|
| PayPal Checkout / Guest Checkout / Pay with Venmo | **3.49% + fixed fee** |
| Standard credit/debit via PayPal | **2.99% + fixed fee** |
| Advanced/Expanded card processing | 2.89% + $0.29 |
| Fixed fee (USD) | **$0.49** (cards-adv. uses $0.29; QR $0.09) |
| PayPal Pay Later | 4.99% + fixed fee |
| QR code | 2.29% + $0.09 |
| Micropayments | 4.99% + $0.09 |
| Virtual terminal | 3.39% |
| Charity | 1.99% |
| International surcharge | **+1.50%** |
| Dispute fee / chargeback fee | **$15 / $20** |
| **Pay With Crypto** | **1.5%** (was 0.99% promo until 31 Jul 2026) |
| PYUSD disbursements via Bill Pay | No fee (1% in the May 2026 schedule — improved) |

Notes: core rates were unchanged between the May, July, and September 2026 schedule revisions — the real 2026 movement was Pay With Crypto repricing and Bill Pay improvements. Effective rates on small transactions are heavily shaped by that $0.49 fixed fee (a $5 sale ≈ 13%; $100 ≈ 4%).

---

## 4. The crypto layer: PYUSD and the 2026 strategy — [VERSIONED]

- **PYUSD supply**: all-time high **~$4.2B in March 2026**, then a **~31% contraction to ~$2.7–2.8B by mid‑2026** as incentive programs tapered and liquidity rotated back to USDT/USDC. That's ~**1.4% of the ~$300B stablecoin market (3rd)**; live across **17 chains**, with **Solana designated the default payment network in Feb 2026**. Peg held $1.00 throughout; Paxos-issued with monthly reserve attestations ([Stablecoin Insider Q2 2026 report](https://stablecoininsider.org/paypals-pyusd-q2-2026-report-supply-adoption-and-key-metrics/), [Cryptonomist](https://en.cryptonomist.ch/2026/08/03/paypal-pyusd-expansion/)).
- **PYUSDx**: a developer platform (PayPal + **M0** + MoonPay) letting businesses launch **their own branded stablecoins backed 1:1 by PYUSD reserves**; reported **$100M+ processed** with launch partners Saturn, Concrete, Cap ([M0 Research](https://research.m0.org/research/paypal-and-m0-launch-developer-platform-for-pyusd-already-crossing-100m-in-scale)).
- **Pay With Crypto** — merchant acceptance of crypto converted at checkout — repriced to 1.5% from 1 Aug 2026 (§3).
- **Agentic commerce**: CEO Enrique Lores framed PYUSD + agentic payments + identity/biometrics as the forward plan; PayPal is among the majors investing in agent-payment infrastructure alongside Stripe/Google/Visa/Mastercard — with the caveat documented in `money-stripe` that flagship agentic-checkout deployments have so far underperformed.
- Developer surface: [PYUSD resource center](https://developer.paypal.com/dev-center/pyusd/) — docs, faucet, Fireblocks API, LayerZero cross-chain tooling, ENS integration (Ethereum + Solana).
- Regulatory frame: PYUSD-as-infrastructure lands inside the **GENIUS Act** regime — final rules pending (Treasury NPRM published 18 Aug 2026; enforcement date **18 Jan 2027** fixed even though regulators missed the July 2026 rulemaking deadline) — see the §7 → `money-stripe` for the full dated picture, because it applies equally here.

---

## 5. Developing on PayPal

### 5.1 The API map

| You want | Use |
|---|---|
| Hosted checkout buttons (fastest) | **PayPal JS SDK** buttons + **Orders v2** API server-side |
| Full card processing, own UX | **Braintree** (Drop-in / custom + payment-method nonces, GraphQL API) |
| Subscriptions | PayPal **Billing Plans/Subscriptions** API (v1) |
| Send mass payouts | **Payouts API** |
| Refunds/voids/captures | Orders v2 (`/v2/payments/authorizations`, `/captures/…/refund`) |
| Webhooks | Webhooks API + signature verification endpoint |
| Marketplace flows | PayPal for Marketplaces (partner-referred onboarding, delayed disbursement) |
| Identity | "Log in with PayPal" (OIDC) |

Two generations coexist: legacy **NVP/SOAP** and **IPN** (don't build new on these) and the current **REST v2 + webhooks** world. **[DURABLE] integration principle identical to Stripe's**: webhooks are the source of truth (at-least-once delivery), the browser redirect is UX only, and you verify + dedupe + re-fetch.

### 5.2 The canonical Orders v2 flow

```bash
# 1. server: create an order (intent: AUTHORIZE for physical goods; CAPTURE for digital)
curl -u $CLIENT:$SECRET -X POST https://api-m.paypal.com/v2/checkout/orders \
  -H "Content-Type: application/json" -H "PayPal-Request-Id: order-$ATTEMPT_ID" \
  -d '{"intent":"CAPTURE","purchase_units":[{"invoice_id":"inv-1042","custom_id":"cart-881",
       "amount":{"currency_code":"USD","value":"49.99"}}]}'
# 2. client: buyer approves in PayPal popup/redirect (JS SDK onApprove)
# 3. server: capture (or authorize now, capture at fulfillment)
curl -u $CLIENT:$SECRET -X POST \
  https://api-m.paypal.com/v2/checkout/orders/$ORDER_ID/capture
```

`PayPal-Request-Id` is PayPal's idempotency key — **[DURABLE] derive it from your internal business attempt ID and persist it before the first call**, exactly as with Stripe (`06-decision-guide.md` has the shared pattern). Amounts are **strings with currency codes**; respect ISO-4217 exponents (JPY: 0 decimals; BHD: 3).

### 5.3 Webhooks — same laws as every PSP

```js
// Verify signature via PayPal's verify API against the RAW body, then dedupe event id, then ACK fast.
const { verification_status } = await paypal.verifyWebhookSignature({
  transmission_id, transmission_time, cert_url, auth_algo,
  transmission_sig, webhook_id: MY_WEBHOOK_ID, webhook_event: rawBodyAsParsed });
if (verification_status !== "SUCCESS") return res.sendStatus(400);
if (await alreadyProcessed(event.id)) return res.sendStatus(200);  // at-least-once delivery
// enqueue work; re-fetch the order from the API rather than trusting the payload
res.sendStatus(200);
```

The event set that costs money when missed: `PAYMENT.CAPTURE.COMPLETED` (fulfill), `PAYMENT.CAPTURE.DENIED`/`DECLINED`, `CUSTOMER.DISPUTE.CREATED` (dispute clock starts), `PAYMENT.PAYOUTS-ITEM.FAILED`, and billing `BILLING.SUBSCRIPTION.*`.

### 5.4 Sandbox vs. live

PayPal's sandbox (developer.paypal.com accounts) covers Orders, subscriptions, payouts, and negative-test scenarios, but **[DURABLE] it differs from production in latency, decline behavior, fraud screening, and webhook timing** — budget for live-only surprises, and run real-money smoke tests at $1 before launch.

### 5.5 PayPal gotchas (the ones practitioners actually hit)

- **Authorize vs capture**: card-style auth windows apply; capture physical-goods payments at shipment, not at order; void rather than abandon auths.
- **Seller Protection is conditional** — address mismatch, intangibles categories, and late shipments void it. Read the eligibility rules before leaning on it in a dispute strategy.
- **Account holds & rolling reserves** are a recurring reality for new/high-risk merchants (up to 90-day holds are documented community experience, not an official schedule); **[DURABLE] mitigation is architectural**: never build so a PSP freeze is existential — secondary PSP, fast payout-to-bank hygiene, cash buffer. Same advice applies verbatim to Stripe and Square.
- **Disputes have short response windows** (typically 10 days at PayPal then card-network timelines); wire `CUSTOMER.DISPUTE.CREATED` to an alerting channel from day one.
- **Currency conversion**: converting inside PayPal is convenient and expensive; present/settle in the currency your customers pay and reconcile from the net.
- **Payouts failures are async**: a Payouts call can "succeed" and the item fails later — the failure arrives by webhook, not by response code.
- **[⚠️ Never log card numbers or CVVs]** — even in Braintree integrations the nonce is fine, the PAN is not; PCI scope follows your logs.

---

## 6. PayPal vs. Stripe vs. both

- **PayPal button + Stripe cards** is the classic conversion-max combo: PayPal's stored-credential wallet lifts mobile/return-buyer conversion; Stripe's card rails are cheaper at the same ticket (2.9%+30¢ vs 3.49%+49¢ US online) and its API is the deeper engineering surface.
- Choose **PayPal-primary** when: your audience skews to it (German/Austrian checkout culture, older US demographics, auction/classifieds commerce), you want PayPal/Venmo/Pay Later with one contract, or you need PayPal's Payouts network.
- Choose **Braintree** when you're already in the PayPal family but need real card-vaulting, marketplace payouts, or a GraphQL API; choose **Stripe Connect** over the PayPal marketplace stack when per-seller tooling, KYC automation, and ledger detail matter most (see §5 → `money-stripe`).
- **PYUSD/Bridge-style stablecoin acceptance** is now offered by both (1.5% each as of Sept 2026) — compare on settlement currency, chain support, and accounting export quality, not on price.

---

## Sources (as of 16 Sep 2026)

[PayPal US merchant fee schedule PDF, eff. 1 Sep 2026](https://www.paypalobjects.com/marketing/ua/pdf/US/us-merchant-fees-01-september-2026.pdf) · [PayPal business fees page](https://www.paypal.com/us/business/fees) · [fee schedule (July 2026 HTML)](https://securepayments.paypal.com/us/business/paypal-business-fees) · [Stablecoin Insider: PYUSD Q2 2026](https://stablecoininsider.org/paypals-pyusd-q2-2026-report-supply-adoption-and-key-metrics/) · [Cryptonomist: Q2 2026 + crypto division](https://en.cryptonomist.ch/2026/08/03/paypal-pyusd-expansion/) · [M0 Research: PYUSDx](https://research.m0.org/research/paypal-and-m0-launch-developer-platform-for-pyusd-already-crossing-100m-in-scale) · [PYUSD resource center](https://developer.paypal.com/dev-center/pyusd/)

Canonical study docs: developer.paypal.com (Orders v2 reference, webhook verifier docs, sandbox guide), Braintree developer docs, PayPal's Seller/Purchase Protection policy pages, and the community blog's PYUSD-for-commerce posts.
