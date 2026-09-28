---
id: skill-7-fraud-and-disputes-8301679835
purpose: 7 fraud and disputes
source: src/vibey_tools/skills/plugins/ecommerce-development/skills/ecommerce-payment-methods-sca-fraud-and-pci/SKILL.md
requires: ["skill-6-sca-3-d-secure-and-authorization-rates-aec0629dff"]
links: ["skill-8-pci-dss-and-security-da9e3e817b"]
---

## §7. Fraud and Disputes

### 7.1 The fraud types

| Type | Who loses | Notes |
|---|---|---|
| **Stolen card / CNP fraud** | **The merchant**, via chargeback | The classic. Liability may shift with 3DS |
| **Friendly fraud / first-party misuse** | The merchant | **The largest category by volume for many merchants**, and the hardest to fight |
| **Account takeover** | Customer and merchant | Protect accounts, not just checkout |
| **Card testing** | Merchant (fees, reputation) | Bots probing stolen numbers with tiny charges. **Rate-limit and CAPTCHA your payment endpoint** |
| **Refund/return abuse** | Merchant | Policy problem more than a technical one |
| **Triangulation, promo abuse, reseller fraud** | Merchant | Business-logic attacks |
| **APP fraud** | The customer (and increasingly the PSP) | Growing with instant rails; ⚠️ **PSD3/PSR shifts liability toward PSPs** — §17 → `ecommerce-reference` |

**[DURABLE] Fraud prevention is an optimization problem with two costs, and teams
systematically optimize only one.** False negatives cost you chargebacks; **false positives
cost you good customers, and are invisible unless you measure them.** A rule set tuned only
on chargeback rate will strangle revenue.

### 7.2 Chargebacks

```
customer disputes → issuer initiates → funds pulled from you + a fee
  → you accept, or REPRESENT with evidence
    → issuer decides → possible pre-arbitration → arbitration (expensive, rare)
```
**⚠️ You lose the fee either way, even when you win.** And **chargeback ratios are
monitored by the networks**; exceeding thresholds puts you in a monitoring program with
fines and, ultimately, loss of processing. **The ratio matters more than the absolute
number.**

**Prevention beats representment**: a clear and recognizable **billing descriptor** (a
startling share of disputes are "I don't recognize this charge"), obvious cancellation and
refund paths, delivery confirmation, pre-renewal notices for subscriptions, and responsive
support. **Order Insight / Consumer Clarity**-style network programs let issuers show
transaction detail in the banking app and deflect disputes before they start.

---
