---
id: skill-3-integration-engineering-a9a2667c92
purpose: 3 integration engineering
source: src/vibey_tools/skills/plugins/ecommerce-development/skills/ecommerce-payments-architecture-and-integration/SKILL.md
requires: ["skill-2-the-payment-lifecycle-e236e24a65"]
links: ["skill-4-psps-and-the-platform-layer-041d325e1c"]
---

## §3. Integration Engineering

**[DURABLE] This is the highest-value section in the document. Most payment bugs in
production are failures of these four things.**

### 3.1 Idempotency

**The problem**: your server sends a charge request. The network times out. **You do not
know whether the charge happened.** Retry and you may double-charge; don't retry and you
may lose the order.

**The solution**: an **idempotency key** on every mutating request. Stripe recommends
adding one to all POST requests; if it receives two requests with the same key, **it
returns the result of the first rather than executing twice**.

```
✓  key = hash(internal_checkout_attempt_id)     // deterministic, survives a crash
⚠️ key = uuid4()                                 // regenerated on retry → useless
```
**[DURABLE] Derive the key from the business action, not from the HTTP request.** A
payment tied to one internal checkout attempt must reuse the same key across all safe
retries — which means **generating and persisting it before the first call**, so a process
crash between generating and sending doesn't lose it. **⚠️ Stripe caches idempotency
results for 24 hours**; after that the same key creates a new request.

### 3.2 Webhooks

**[DURABLE] Webhooks are at-least-once, never exactly-once. That single fact drives every
operational decision.**

```
1. VERIFY THE SIGNATURE against the RAW request body — before parsing.
   ⚠️ Skip this and anyone can POST fake payment events to your endpoint.
2. RETURN 200 IMMEDIATELY. Process asynchronously.
   Stripe times out at ~30s and retries; a slow handler looks like a failure.
3. DEDUPLICATE on the event ID:
   INSERT event_id INTO processed_events  -- unique constraint
   -- unique violation → already handled → skip
4. Then do the work, in a transaction.
5. Re-fetch the resource from the API rather than trusting the payload.
```

> **⚠️ GOTCHA — the webhook failures that cost real money:**
> - **Fulfilling on the redirect URL instead of the webhook.** The user closes the tab
>   before redirecting and the order never completes. **The webhook is the source of
>   truth; the redirect is a UX nicety.**
> - **Non-idempotent handlers.** One practitioner reports observing the same
>   `checkout.session.completed` delivered **three times within 60 seconds** during a
>   provider infrastructure event, causing triple-provisioning.
> - **Returning 200 before processing** — the event is now lost, with no retry coming.
> - **Handling only the happy path.** A system that handles `invoice.paid` but not
>   `invoice.payment_failed` leaves users on paid tiers after their card declines.
>   **At scale this is quiet, continuous revenue leakage.**
> - **Assuming ordering.** Events can arrive out of order. Check the resource's current
>   state, don't infer it from event sequence.
> - **No dead-letter queue** for events that fail repeatedly.
>
> Stripe retries for **up to ~72 hours** with backoff, which is your safety net — but only
> if your endpoint returns non-2xx on genuine failure rather than swallowing errors.

### 3.3 Reconciliation

**[DURABLE] Your database and your processor's records will diverge. Plan for it.**
A nightly job comparing your orders against the processor's records for the past 24–48
hours surfaces discrepancies before they become financial disputes. Reconcile:
**auth vs. capture vs. settlement**, **your order total vs. the settled amount net of
fees**, **refunds issued vs. refunds settled**, and **payouts vs. the sum of their
constituent transactions**.

**[DURABLE] Build a ledger.** Double-entry, append-only, one row per money movement, never
updated in place. It is the only structure that survives partial refunds, disputes,
multi-currency, and an auditor. **Retrofitting a ledger after eighteen months of
production data is one of the worst projects in this domain** — do it at the start.

### 3.4 Error handling

**Decline vs. error vs. indeterminate** are three different things and need three
different behaviours. **⚠️ Treat a 500 or a timeout as *indeterminate*, not as failure** —
Stripe's own guidance is explicit that a 500 request's result is indeterminate, that they
attempt to reconcile such requests, and that you should configure webhook handlers to
receive event objects you'd never see in a normal API response.

**Retry with exponential backoff and jitter**, only on 5xx and network errors, **always
with the same idempotency key**, and with a cap.

**Never log full card numbers, CVVs, or API secrets** — this puts your logging
infrastructure in PCI scope (§8 → `ecommerce-payment-methods-sca-fraud-and-pci`) and it happens constantly. **Rotate any key that has ever
been committed to version control; assume it is compromised.**

---
