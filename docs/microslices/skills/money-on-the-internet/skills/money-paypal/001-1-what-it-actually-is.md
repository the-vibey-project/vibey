---
id: skill-1-what-it-actually-is-2c978e9cfb
purpose: 1 what it actually is
source: src/vibey_tools/skills/plugins/money-on-the-internet/skills/money-paypal/SKILL.md
requires: []
links: ["skill-2-using-it-3a38ccd9b5"]
---

## 1. What it actually is

PayPal is three things stacked: a **consumer account network** (~hundreds of millions of accounts; Q2 2026 total payment volume **$486.4B, +10% YoY**, net revenue $8.68B — [Cryptonomist on Q2 2026](https://en.cryptonomist.ch/2026/08/03/paypal-pyusd-expansion/)), a **merchant PSP/gateway** (PayPal Checkout, plus **Braintree** for full-stack card processing and **Venmo** acceptance), and — since 2023 — a **stablecoin issuer** (PYUSD). In 2026 PayPal formally combined PYUSD with Braintree merchant processing into a single **"Payment Services & Crypto" division**.

The structural fact that separates PayPal (and Stripe) from everything in the chain skills (`money-bitcoin`, `money-ethereum`, `money-monero`): **PayPal operates entirely inside the regulated banking system, and is itself the counterparty that can reverse, hold, and freeze.** That's what makes it usable for mainstream commerce — buyer protection, chargebacks, fiat settlement — and also what makes account risk (§4) a design input rather than an edge case.

---
