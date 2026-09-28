---
id: skill-2-the-payment-lifecycle-e236e24a65
purpose: 2 the payment lifecycle
source: src/vibey_tools/skills/plugins/ecommerce-development/skills/ecommerce-payments-architecture-and-integration/SKILL.md
requires: ["skill-1-architecture-8f41d02cf7"]
links: ["skill-3-integration-engineering-a9a2667c92"]
---

## §2. The Payment Lifecycle

### 2.1 What actually happens

```
CUSTOMER → merchant → PSP/gateway → acquirer → CARD NETWORK → issuer
                                                                 │
   authorization decision ←──────────────────────────────────────┘
   (approve / decline / soft decline requiring SCA)

then, separately and later:
   CAPTURE  → clearing → SETTLEMENT (funds move, T+1 to T+3) → payout to you
```

**[DURABLE] The distinction that matters most: authorization ≠ capture ≠ settlement ≠
payout, and they happen at different times.**

| Step | What it is | Notes |
|---|---|---|
| **Authorization** | Issuer holds funds and promises them | Expires (~7 days typical, varies). Reduces the customer's available balance immediately |
| **Capture** | You claim the authorized funds | Can be partial. **Capture at fulfillment for physical goods, at purchase for digital** |
| **Void / reversal** | Cancel an uncaptured auth | **Always void rather than leaving an auth to expire** — the customer's money is held otherwise |
| **Clearing & settlement** | Networks and banks move real money | T+1 to T+3 typically |
| **Payout** | PSP sends you the net | Net of fees, refunds, chargebacks, reserves |
| **Refund** | Money back to the original method | ⚠️ Days to appear. **Fees are often not refunded** |
| **Chargeback** | Customer disputes via their bank | §7 → `ecommerce-payment-methods-sca-fraud-and-pci` |

**⚠️ The single most common junior mistake: treating a successful authorization as
"paid."** It isn't. It's a promise that can be voided, expire, fail at capture, or be
reversed. **Fulfil on capture, not on auth** — and even then, see §7 → `ecommerce-payment-methods-sca-fraud-and-pci`.

### 2.2 Amounts and money handling

**[DURABLE] Never use floating point for money.** `0.1 + 0.2 != 0.3`, and in a financial
system that becomes a reconciliation discrepancy nobody can explain. **Use integer minor
units** (cents) or an arbitrary-precision decimal type.

**⚠️ Not every currency has 2 decimal places.** JPY and KRW have 0; BHD, KWD, and JOD have
3. A hardcoded `× 100` breaks in those markets. **Use the ISO 4217 exponent.**

**Always store the currency with the amount.** An `amount` column without a `currency`
column is a bug waiting for your first international order. And **store the original
amount and currency alongside any converted values** — never only the converted figure.

**Rounding**: decide the rule, document it, apply it consistently, and **reconcile
line-item rounding against the order total** — tax and discount allocation across line
items is where the cents go missing.

---
