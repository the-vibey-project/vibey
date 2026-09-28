---
id: skill-5-money-movement-products-pricing-us-as-of-sept-2026-9a5b731519
purpose: 5 money movement products pricing us as of sept 2026
source: src/vibey_tools/skills/plugins/money-on-the-internet/skills/money-stripe/SKILL.md
requires: ["skill-4-compliance-reality-us-eu-as-of-2026-af5c1666a1"]
links: ["skill-6-the-stablecoin-stack-bridge-privy-tempo-versioned-fast-moving-45b1497ada"]
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
