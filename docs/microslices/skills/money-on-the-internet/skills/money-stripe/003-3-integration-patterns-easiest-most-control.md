---
id: skill-3-integration-patterns-easiest-most-control-d7482527af
purpose: 3 integration patterns easiest most control
source: src/vibey_tools/skills/plugins/money-on-the-internet/skills/money-stripe/SKILL.md
requires: ["skill-2-core-api-mechanics-durable-f081efc547"]
links: ["skill-4-compliance-reality-us-eu-as-of-2026-af5c1666a1"]
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
