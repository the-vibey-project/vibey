---
id: skill-4-psps-and-the-platform-layer-041d325e1c
purpose: 4 psps and the platform layer
source: src/vibey_tools/skills/plugins/ecommerce-development/skills/ecommerce-payments-architecture-and-integration/SKILL.md
requires: ["skill-3-integration-engineering-a9a2667c92"]
links: []
---

## §4. PSPs and the Platform Layer

### 4.1 The categories

| Layer | What it does | Examples |
|---|---|---|
| **Payment gateway** | Transmits transaction data | Increasingly bundled |
| **Payment processor / acquirer** | Moves money, holds the merchant relationship | Chase Paymentech, Worldpay, Elavon |
| **PSP / aggregator** | Gateway + processing + your merchant account under theirs | **Stripe, PayPal, Square, Adyen, Braintree, Mollie, Razorpay** |
| **Orchestration** | Routes across multiple PSPs | Gr4vy, Primer, Spreedly |
| **Merchant of record (MoR)** | **Sells as the legal seller — takes on tax and compliance** | Paddle, Lemon Squeezy, FastSpring |

**[DURABLE] The MoR option deserves more consideration than it gets**, especially for
digital goods sold internationally. They become the legal seller, which means **they own
VAT/GST registration and remittance across jurisdictions** (§11 → `ecommerce-billing-tax-platforms-and-checkout`) — often the single
largest hidden cost for a small team selling globally. You pay a higher rate for it.

### 4.2 Choosing

**Ask about**: pricing (headline rate *plus* cross-border, currency conversion, chargeback,
and payout fees — **the effective rate is what matters, and it is never the headline**),
supported methods and geographies, **payout timing and reserves** (a 90-day rolling reserve
is a cash-flow event, not a footnote), API and SDK quality, webhook reliability, dispute
tooling, **account stability** (aggregators can and do freeze accounts — have a fallback),
and **data portability**: can you migrate stored payment credentials to another provider?
Networks support this and providers will facilitate it, but **ask before you're locked in**.

**⚠️ Test mode is not production.** Sandbox environments differ in latency, decline
behaviour, webhook timing, and edge cases. Budget for problems that only appear on live
traffic.

### 4.3 API versioning

**[DURABLE]** Payment APIs pin a version per account or per request, which is a genuine
kindness — but it means **your integration silently ages**. Upgrading is a real project
with behaviour changes. Track your pinned version, read the changelogs, and **upgrade
deliberately on a schedule** rather than discovering you're four years behind during an
incident.
