---
id: skill-1-architecture-8f41d02cf7
purpose: 1 architecture
source: src/vibey_tools/skills/plugins/ecommerce-development/skills/ecommerce-payments-architecture-and-integration/SKILL.md
requires: ["skill-0-routing-bf7dcaf98d"]
links: ["skill-2-the-payment-lifecycle-e236e24a65"]
---

## §1. Architecture

### 1.1 The shape of the system

```
STOREFRONT ─── catalog · search · cart ─── CHECKOUT ─── payment
    │                                          │
    ├── CMS / merchandising                    ├── fraud screening
    ├── pricing & promotions                   ├── tax calculation
    └── personalization / recs                 └── address validation
                                               │
                                        ORDER MANAGEMENT (OMS)
                                               │
        ┌──────────────┬────────────────┬──────┴──────┬─────────────┐
     inventory     fulfillment      payments        tax         customer
     (ATP, holds)  (WMS, 3PL,       (capture,     (remittance)  (accounts,
                   shipping)         refunds,                    support)
                                     payouts)
                                               │
                                     LEDGER + RECONCILIATION
                                               │
                                          accounting / ERP
```

**[DURABLE] The hard parts are not where people expect.** Rendering a product page is
solved. The genuinely difficult problems are:
- **Inventory correctness under concurrency** — overselling is a customer-facing failure
  and an operational one. Reserve at cart or at order? For how long?
- **Order state as a distributed transaction** across payment, inventory, and fulfillment
  systems that can each fail independently.
- **Money movement correctness** (§2, §3).
- **Tax** (§11 → `ecommerce-billing-tax-platforms-and-checkout`) — deceptively deep.
- **Returns and partial fulfillment**, which turn a clean order model into a graph.

### 1.2 The order state machine

**[DURABLE] Model the order explicitly as a state machine, and make every transition
idempotent and logged.** Ad-hoc boolean flags (`is_paid`, `is_shipped`) collapse under
partial refunds, partial shipments, and cancellations.

```
created → payment_pending → payment_authorized → confirmed
   → [partially_]fulfilled → completed
        ↘ payment_failed   ↘ cancelled   ↘ [partially_]refunded  ↘ disputed
```
**⚠️ The states people forget**: authorized-but-not-captured (and the auth expiring —
typically ~7 days for card auths, shorter for some methods), partially captured, partially
refunded, refunded-after-dispute, and **fulfilled-then-chargebacked** (you have neither
the goods nor the money).

### 1.3 Consistency

**[DURABLE] You cannot have a distributed transaction across a payment processor, your
database, and a warehouse.** So you use **sagas with compensating actions**: authorize
payment → reserve inventory → if reservation fails, void the authorization. Design the
compensations *first*; they're the part that gets skipped and the part that matters.

**The outbox pattern** is the standard answer for "update the database and emit an event
atomically": write the event to an outbox table in the same transaction, then a relay
publishes it. Without it, you get orders that exist with no downstream notification, or
notifications for orders that rolled back.

**⚠️ Never make an external payment call inside a database transaction.** The call takes
seconds, holds locks, and if it times out you have no idea whether it succeeded — while
holding a transaction open. Authorize first, then record, with idempotency to make the
retry safe (§3.1).

---
