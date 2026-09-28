---
id: skill-2-decision-heuristics-54ba0e9f84
purpose: 2 decision heuristics
source: src/vibey_tools/skills/plugins/money-on-the-internet/skills/money-choosing-a-rail-and-shared-patterns/SKILL.md
requires: ["skill-1-side-by-side-all-dated-claims-are-as-of-16-sep-2026-6c29ae4f33"]
links: ["skill-3-the-four-engineering-patterns-that-transfer-everywhere-78ed7c0d95"]
---

## 2. Decision heuristics

- **Selling online, mainstream customers** → Stripe Checkout/Payment Element as primary; **add the PayPal button** (and wallets) for conversion. Digital goods sold globally: price **Managed Payments / an MoR** (Paddle etc.) before hand-rolling tax — VAT/sales-tax nexus is the cost everyone discovers late.
- **Marketplace / paying third parties** → Stripe Connect (or PayPal for Marketplaces / Adyen for Platforms). Building the money movement yourself = money-transmitter licensing; almost never the right call.
- **Customers want to pay in crypto** → 2026 default: **stablecoin acceptance via a PSP** (Stripe ≥1.5% or PayPal "Pay With Crypto" 1.5%) — you get dollars, no keys, no reorg handling. Self-custodial acceptance is only worth it when: you specifically serve crypto-native customers, want no intermediary fee/censorship, or operate where PSPs won't have you. If so: accept **Bitcoin via Lightning** or **a major stablecoin on a mature L2**; treat Monero acceptance as a deliberate privacy/regulatory posture, not a feature checkbox.
- **You need actual privacy (donations under duress, political edge cases, fungibility)** → Monero, self-custody, P2P acquisition, and go in eyes-open about the shrinking regulated perimeter (Kraken US still lists XMR; Binance/Coinbase do not; EU institutions exit by Jul 2027).
- **Building *new* money infrastructure** → the crowded middle is stablecoins: Bridge Open Issuance / PYUSDx / GENIUS-regulated issuance, settling on Ethereum L2s or purpose chains like Tempo. The durable edges are unchanged: BTC as the censorship-resistant reserve asset; XMR as the privacy primitive.
- **Never make any single PSP existential**: secondary PSP, payout discipline, cash buffer. Applies identically to PayPal, Stripe, Square, Adyen.
