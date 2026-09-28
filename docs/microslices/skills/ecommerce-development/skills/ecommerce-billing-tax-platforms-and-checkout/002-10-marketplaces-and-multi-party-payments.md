---
id: skill-10-marketplaces-and-multi-party-payments-da2bffdb03
purpose: 10 marketplaces and multi party payments
source: src/vibey_tools/skills/plugins/ecommerce-development/skills/ecommerce-billing-tax-platforms-and-checkout/SKILL.md
requires: ["skill-9-subscriptions-and-billing-f3165c31c5"]
links: ["skill-11-tax-and-cross-border-c9972da7e1"]
---

## §10. Marketplaces and Multi-Party Payments

**[DURABLE] The moment money flows to someone other than you, the compliance surface
changes dramatically.** You may be handling funds on behalf of third parties, which in many
jurisdictions is a regulated activity.

**The standard answer: use a PSP's multi-party product** (Stripe Connect, PayPal for
Marketplaces, Adyen for Platforms) so they carry the licensing, KYC/KYB, and payout
infrastructure. **Building this yourself means money-transmitter licensing in the US
(state by state) or a payment institution licence in the EU** — a multi-year, multi-million
undertaking that is almost never the right call.

**What you still own**: onboarding and **KYC/KYB** verification flows, the **split logic**
(platform fee, seller net, tax), **payout scheduling and reserves**, **negative balances**
(a seller refunds after you've paid them out — who eats it?), and **1099-K / DAC7 reporting**.

**⚠️ Chargeback liability in a marketplace is a contract question with a technical
implementation.** Decide explicitly whether the platform or the seller bears it, and build
the ledger to reflect that decision.

---
