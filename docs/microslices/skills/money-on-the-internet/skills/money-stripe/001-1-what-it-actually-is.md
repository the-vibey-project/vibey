---
id: skill-1-what-it-actually-is-aa07846846
purpose: 1 what it actually is
source: src/vibey_tools/skills/plugins/money-on-the-internet/skills/money-stripe/SKILL.md
requires: []
links: ["skill-2-core-api-mechanics-durable-f081efc547"]
---

## 1. What it actually is

Stripe is a **developer-first PSP/aggregator**: gateway + processing + a pooled merchant account under Stripe's, sold through APIs. The 2026 surface: **Payments** (PaymentIntents, Checkout, Payment Links), **Billing** (subscriptions, invoicing, usage/metering), **Connect** (multi-party payments), **Radar** (fraud ML), **Terminal** (in-person), **Issuing** (cards), **Tax**, **Identity/Crypto onboarding**, **Financial Connections**, **Managed Payments** (merchant-of-record, added April 2026), and a **stablecoin stack** (Bridge, Privy, Tempo — §6).

**[DURABLE] The one mental model that pays for itself**: Stripe is a state machine API over the card/bank networks. You are never "charging a card"; you are moving a **PaymentIntent** through `requires_payment_method → requires_confirmation → requires_action (3DS) → processing → succeeded` (or `requires_capture` if auth-only), with **webhooks announcing transitions**. Authorization ≠ capture ≠ settlement ≠ payout — they happen at different times and can fail independently. Fulfil physical goods on **capture**, ideally funded by the webhook, never on a redirect.

---
