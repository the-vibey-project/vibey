---
id: skill-14-agentic-commerce-893ac8a9b0
purpose: 14 agentic commerce
source: src/vibey_tools/skills/plugins/ecommerce-development/skills/ecommerce-billing-tax-platforms-and-checkout/SKILL.md
requires: ["skill-13-catalog-cart-and-checkout-a8752b82f8"]
links: []
---

## §14. Agentic Commerce

**[VERSIONED — the newest layer here, moving fast, and full of premature certainty.]**

### 14.1 What it is

AI agents completing purchases on a user's behalf, which breaks the classic model where **a
human clicks buy on a trusted page**. That assumption underpins fraud liability, SCA, and
dispute rights, so the protocols exist mainly to answer: **how does the merchant know this
agent is authorized, and who is accountable when it goes wrong?**

### 14.2 The standards contest

| Protocol | Origin | Layer |
|---|---|---|
| **ACP** (Agentic Commerce Protocol) | **OpenAI + Stripe**, Sept 2025, Apache 2.0 | Agent-to-merchant **checkout**; shared payment tokens |
| **UCP** (Universal Commerce Protocol) | **Google + Shopify**, announced at NRF Jan 2026 | Full journey — **discovery through post-purchase** |
| **AP2** (Agent Payments Protocol) | **Google**, 60+ partners; **donated to the FIDO Alliance 28 April 2026** with v0.2 | **Authorization and accountability** — cryptographically signed mandates / verifiable credentials |
| **x402** | Coinbase | HTTP 402 revival for **stablecoin machine-to-machine micropayments** |
| **MPP** (Machine Payments Protocol) | Stripe + Tempo, **18 March 2026** | Agent pre-authorizes a spending limit, streams micropayments |
| **Visa Trusted Agent Protocol / Mastercard Agent Pay** | The networks | Agent-scoped tokenization on existing rails |

**⚠️ These are not interchangeable and they sit at different layers.** A plausible reading
of where it settles: **UCP-style discovery and cart standards, AP2-style verifiable
authorization underneath, and execution layers each major AI surface adopts its own way.**

### 14.3 The reality check

**⚠️ The obvious narrative is wrong in an instructive way. OpenAI's Instant Checkout —
the launch product for ACP, which put ChatGPT purchasing in front of the largest consumer
AI audience — was retired on 5 March 2026**, after roughly thirty Shopify merchants
integrated, with OpenAI pivoting to retailer-operated ChatGPT Apps. And **Forrester's data
shows US consumer adoption of Instant Checkout remained low and stagnant from debut to
discontinuation**; interest in AI agents making purchases is growing but described as
lukewarm.

**[CONTESTED] So: is this real?** *For building now*: the infrastructure investment from
Stripe, Google, Shopify, Visa, Mastercard and PayPal is enormous, the standards are
consolidating rather than proliferating, and being invisible to agent-mediated discovery is
a genuine risk if it lands. *Against*: consumer demand has not yet materialized, the
flagship implementation was withdrawn within six months, and the protocols are still
churning — **ACP's own spec history shows five revisions between September 2025 and April
2026.**

**[DURABLE] The advice that holds either way is not really about agents:** the thing that
makes you legible to an AI agent is **clean, accurate, machine-readable product data** —
precise titles, real-time stock and pricing, clear specs, standards-based schema, and a
catalog API that doesn't require executing your JavaScript. **That work pays off in search,
in marketplaces, in feeds, and in agent surfaces alike**, which makes it the rare hedge
with no downside. **Adopt a payment standard rather than building your own agent-payment
flow** — rolling your own means inheriting all the fraud liability yourself.
