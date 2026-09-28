---
id: skill-19-quick-reference-47a309d270
purpose: 19 quick reference
source: src/vibey_tools/skills/plugins/ecommerce-development/skills/ecommerce-reference/SKILL.md
requires: ["skill-18-the-canon-829f69bb7e"]
links: ["skill-20-sources-and-method-d80cf0ca69"]
---

## §19. Quick Reference

### 19.1 Numbers
- Card authorization holds: **~7 days** typical, varies by network and method.
- Settlement: **T+1 to T+3** typical.
- Stripe webhook retries: **up to ~72 hours**; **respond within ~30s**.
- Stripe idempotency cache: **24 hours**.
- ACH consumer reversals: **up to 60 days**. SEPA DD refund right: **8 weeks**.
- PCI DSS v4.0.1 future-dated requirements mandatory: **31 March 2025**.
- Requirement **11.6.1** tamper detection: evaluate **at least weekly**.
- Verification of Payee (euro-area, instant): **since 9 October 2025**.
- European Accessibility Act: **enforceable since 28 June 2025**.
- Currency decimals: **JPY/KRW = 0 · most = 2 · KWD/BHD/JOD = 3**.

### 19.2 Payment integration checklist
- [ ] Idempotency key on every mutating call, **derived from the business action and
      persisted before the call**
- [ ] Webhook signature verified against the **raw body**
- [ ] Webhook handler deduplicates on event ID with a **unique constraint**
- [ ] 200 returned fast; work done async; failures return non-2xx so retries happen
- [ ] Dead-letter queue for repeatedly failing events
- [ ] **Fulfilment triggered by webhook, never by redirect**
- [ ] Failure events handled, not just success events
- [ ] 5xx/timeouts treated as indeterminate and reconciled
- [ ] Nightly reconciliation job against the processor
- [ ] Append-only ledger recording every money movement
- [ ] Amounts in minor units with currency; ISO 4217 exponents respected
- [ ] Auths voided rather than left to expire
- [ ] No PAN, CVV, or secret in any log, ever
- [ ] Payment endpoints rate-limited against card testing
- [ ] Billing descriptor recognizable to a human
- [ ] Authorization rate instrumented and monitored
- [ ] PCI SAQ type confirmed — **including SAQ A eligibility under the 2025 criterion**

### 19.3 Triage
| Symptom | First look |
|---|---|
| Customer charged twice | Idempotency key regenerated on retry (§3.1 → `ecommerce-payments-architecture-and-integration`) |
| Order paid but never created | Fulfilment on redirect instead of webhook (§3.2 → `ecommerce-payments-architecture-and-integration`) |
| Duplicate fulfilment / double provisioning | Non-idempotent webhook handler (§3.2 → `ecommerce-payments-architecture-and-integration`) |
| Revenue quietly lower than expected | Unhandled `payment_failed` events; dunning (§3.2 → `ecommerce-payments-architecture-and-integration`, §9 → `ecommerce-billing-tax-platforms-and-checkout`) |
| Your totals ≠ processor's totals | No reconciliation; rounding allocation; fees (§2.2 → `ecommerce-payments-architecture-and-integration`, §3.3 → `ecommerce-payments-architecture-and-integration`) |
| Auth rate dropped | Card-on-file expiry, missing network tokens, routing change, 3DS config (§6.2 → `ecommerce-payment-methods-sca-fraud-and-pci`) |
| Conversion drops in one country | Wrong payment methods for that market (§5.2 → `ecommerce-payment-methods-sca-fraud-and-pci`) |
| Chargebacks rising | Descriptor recognition, delivery evidence, subscription notices (§7.2 → `ecommerce-payment-methods-sca-fraud-and-pci`) |
| Failed a PCI assessment on scope | Card data or scripts touching systems you thought were out of scope (§8 → `ecommerce-payment-methods-sca-fraud-and-pci`) |
| Checkout abandonment spike at the last step | Surprise shipping/tax/duty (§13.2 → `ecommerce-billing-tax-platforms-and-checkout`, §11 → `ecommerce-billing-tax-platforms-and-checkout`) |
| Cents missing on multi-item orders | Rounding allocation across line items (§2.2 → `ecommerce-payments-architecture-and-integration`) |

---
