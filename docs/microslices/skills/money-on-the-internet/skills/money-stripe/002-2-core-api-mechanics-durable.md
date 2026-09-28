---
id: skill-2-core-api-mechanics-durable-f081efc547
purpose: 2 core api mechanics durable
source: src/vibey_tools/skills/plugins/money-on-the-internet/skills/money-stripe/SKILL.md
requires: ["skill-1-what-it-actually-is-aa07846846"]
links: ["skill-3-integration-patterns-easiest-most-control-d7482527af"]
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
