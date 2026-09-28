---
id: skill-15-anti-patterns-989a3eeeb0
purpose: 15 anti patterns
source: src/vibey_tools/skills/plugins/ecommerce-development/skills/ecommerce-reference/SKILL.md
requires: []
links: ["skill-16-contested-questions-e3d9ce0f7a"]
---

## §15. Anti-Patterns

| Anti-pattern | Why | Instead |
|---|---|---|
| Floating point for money | `0.1 + 0.2 != 0.3` → unexplainable discrepancies | Integer minor units or decimal (§2.2 → `ecommerce-payments-architecture-and-integration`) |
| Hardcoding `× 100` | JPY/KRW have 0 decimals; KWD/BHD have 3 | ISO 4217 exponent (§2.2 → `ecommerce-payments-architecture-and-integration`) |
| Amount column with no currency | Breaks on your first international order | Always store both |
| Treating authorization as payment | It can expire, fail at capture, or be voided | Fulfil on capture (§2.1 → `ecommerce-payments-architecture-and-integration`) |
| Leaving auths to expire instead of voiding | The customer's money stays held | Void explicitly (§2.1 → `ecommerce-payments-architecture-and-integration`) |
| Random UUID as the idempotency key | Regenerated on retry → no protection at all | Derive from the business action, persist before calling (§3.1 → `ecommerce-payments-architecture-and-integration`) |
| Fulfilling on the redirect URL | Customer closes the tab; order lost | **Webhook is the source of truth** (§3.2 → `ecommerce-payments-architecture-and-integration`) |
| Non-idempotent webhook handler | Same event delivered 3× in 60s is documented | Unique constraint on event ID (§3.2 → `ecommerce-payments-architecture-and-integration`) |
| Returning 200 before processing | Event lost, no retry | 200 immediately, process async, but only after durably recording it |
| Handling only the happy path | `invoice.paid` without `invoice.payment_failed` = silent revenue leak | Handle failures (§3.2 → `ecommerce-payments-architecture-and-integration`) |
| Treating a 500/timeout as failure | The result is **indeterminate** | Retry with the same key; reconcile (§3.4 → `ecommerce-payments-architecture-and-integration`) |
| Retrying hard declines | Futile and a compliance problem | Soft only (§6.2 → `ecommerce-payment-methods-sca-fraud-and-pci`) |
| No reconciliation job | Divergence found by an auditor, not by you | Nightly reconciliation (§3.3 → `ecommerce-payments-architecture-and-integration`) |
| No ledger, or a mutable one | Partial refunds and disputes destroy it | Append-only double-entry, from day one (§3.3 → `ecommerce-payments-architecture-and-integration`) |
| External payment call inside a DB transaction | Locks held across a network call of unknown outcome | Call first, then record (§1.3 → `ecommerce-payments-architecture-and-integration`) |
| Boolean flags instead of an order state machine | Collapses on partial refunds/shipments | Explicit states and transitions (§1.2 → `ecommerce-payments-architecture-and-integration`) |
| Card data touching your servers or logs | Puts your whole stack in PCI scope | Hosted fields/iframe; store tokens (§8.1 → `ecommerce-payment-methods-sca-fraud-and-pci`) |
| Assuming the SAQ A change reduced your obligations | **The criterion now covers your entire site, not just the payment page** | Read §8.2 → `ecommerce-payment-methods-sca-fraud-and-pci`. Confirm eligibility or file SAQ A-EP |
| Loading many third-party scripts on checkout | Every tag is a Magecart vector on your highest-value page | Minimize; CSP + SRI (§8.3 → `ecommerce-payment-methods-sca-fraud-and-pci`) |
| Optimizing fraud rules on chargeback rate alone | False positives are invisible and expensive | Measure both error types (§7.1 → `ecommerce-payment-methods-sca-fraud-and-pci`) |
| Vague billing descriptor | A large share of disputes is "I don't recognize this" | Recognizable descriptor (§7.2 → `ecommerce-payment-methods-sca-fraud-and-pci`) |
| Ignoring involuntary churn | Often the largest churn component | Smart dunning + account updater (§9 → `ecommerce-billing-tax-platforms-and-checkout`) |
| Hard-to-cancel subscriptions | Chargebacks, and a growing regulatory problem | Cancel as easily as signup (§9 → `ecommerce-billing-tax-platforms-and-checkout`) |
| Building marketplace payouts yourself | Money transmission licensing | Use a multi-party PSP product (§10 → `ecommerce-billing-tax-platforms-and-checkout`) |
| Hardcoded tax rates | A liability, not a shortcut | Tax engine, or a merchant of record (§11 → `ecommerce-billing-tax-platforms-and-checkout`) |
| Surprise costs at the final checkout step | Top cited abandonment cause | Show all costs early (§13.2 → `ecommerce-billing-tax-platforms-and-checkout`) |
| Forced account creation | Among the most damaging checkout choices | Guest checkout (§13.2 → `ecommerce-billing-tax-platforms-and-checkout`) |
| One payment method for every market | Silently caps conversion abroad | Localize the method mix (§5.2 → `ecommerce-payment-methods-sca-fraud-and-pci`) |
| Never measuring authorization rate | Usually worth more than front-end CVR work | Instrument it (§6.2 → `ecommerce-payment-methods-sca-fraud-and-pci`) |
| Building a bespoke agent-payment flow | You inherit all the fraud liability | Adopt a standard (§14.3 → `ecommerce-billing-tax-platforms-and-checkout`) |
| Assuming sandbox behaviour equals production | Latency, declines, webhook timing all differ | Budget for live-traffic surprises (§4.2 → `ecommerce-payments-architecture-and-integration`) |
| Committing an API key "temporarily" | Assume compromised the moment it lands | Rotate immediately; secrets manager (§3.4 → `ecommerce-payments-architecture-and-integration`) |

---
