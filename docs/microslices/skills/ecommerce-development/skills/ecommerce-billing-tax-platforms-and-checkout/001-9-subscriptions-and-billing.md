---
id: skill-9-subscriptions-and-billing-f3165c31c5
purpose: 9 subscriptions and billing
source: src/vibey_tools/skills/plugins/ecommerce-development/skills/ecommerce-billing-tax-platforms-and-checkout/SKILL.md
requires: []
links: ["skill-10-marketplaces-and-multi-party-payments-da2bffdb03"]
---

## §9. Subscriptions and Billing

**[DURABLE] Billing is where the interesting bugs live**, because it is a state machine
running unattended for years.

**The model**: customer → subscription → plan/price → invoice → payment attempt →
(success | dunning). **Proration** on mid-cycle changes is the classic source of
disagreement between your invoice and the customer's expectations — **decide the policy,
document it, and show the math on the invoice.**

**Dunning** — the retry sequence on failed payments — is directly revenue-relevant. **Smart
retry timing** (aligned with paydays and issuer behaviour) recovers materially more than
fixed daily retries. Combine with **card account updater**, pre-dunning notices before
expiry, and a clear in-product update path.

**⚠️ Involuntary churn — failed payments, not cancellations — is often the largest single
churn component, and it is the most tractable.** Teams obsess over the cancel flow and
ignore the retry logic.

**Also handle**: trials (and the conversion charge), **upgrade/downgrade proration**,
pausing, usage-based and metered billing (with idempotent usage records — double-counted
usage is a support nightmare), tax on recurring charges as the customer moves jurisdiction,
and **revenue recognition** (ASC 606 / IFRS 15 — cash received ≠ revenue recognized, and
your finance team needs the deferred-revenue schedule).

**⚠️ Make cancellation as easy as signup.** Beyond being decent, "negative option" and
click-to-cancel rules in several jurisdictions increasingly require it, and dark-pattern
cancellation flows are a regulatory and chargeback risk.

---
