---
id: skill-5-developing-on-paypal-9cdc0ec28b
purpose: 5 developing on paypal
source: src/vibey_tools/skills/plugins/money-on-the-internet/skills/money-paypal/SKILL.md
requires: ["skill-4-the-crypto-layer-pyusd-and-the-2026-strategy-versioned-8327f03de7"]
links: ["skill-6-paypal-vs-stripe-vs-both-f754404bf4"]
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
