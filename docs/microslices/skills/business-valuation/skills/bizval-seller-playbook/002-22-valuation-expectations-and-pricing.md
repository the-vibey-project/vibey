---
id: skill-22-valuation-expectations-and-pricing-aa05572b09
purpose: 22 valuation expectations and pricing
source: src/vibey_tools/skills/plugins/business-valuation/skills/bizval-seller-playbook/SKILL.md
requires: ["skill-21-exit-readiness-7caafd3e3c"]
links: ["skill-23-advisors-and-process-00701669f5"]
---

## §22. Valuation Expectations and Pricing

### 22.1 Get an honest range
Use §10–§15 on **normalized** earnings; consider an **independent valuation or sell-side QoE** before listing; check the **comps for your size** (**BizBuySell: ~2.7× SDE average, median price $349,250 and median cash flow $155,921; GF Data PE middle market 7.0×**) and apply **size/growth/recurring/concentration** adjustments. **Typical failure:** an owner anchors on a past or industry-folklore multiple, lists high, and the listing **sits and stales**.
**Ask vs sell:** the *ask* is not the *price*; **overpriced listings** often lengthen marketing time and **signal desperation when cut**. A broker's opinion of value is a **marketing tool**.

### 22.2 Price components and your PV
Compute the **risk-adjusted PV** of each offer:
`deal_pv(cash_at_close, seller_note, note_rate, note_years, earnout_max, earnout_prob, earnout_year, rollover_value, rollover_haircut, discount_rate, escrow)`.
| Offer | Headline | **PV to seller (12% discount rate)** | Cash at close |
|---|---|---|---|
| A: all cash | $4.30M | **$4.30M** | 100% |
| B: structured | $5.25M | **$4.60M** (87.5%) | 57% |
**B beats A by ~$0.30M if the buyer's note is credit-good, earnout probability is realistic and you accept illiquid rollover:** otherwise A. Adjust the discount rate to *your* alternative uses of cash and the **buyer's credit risk**.

### 22.3 Net proceeds waterfall
`Price → − debt/payoffs − debt-like items − transaction costs (advisor fees, legal) − taxes − escrow (delayed) → net`. **Transaction costs** (Main Street broker commissions commonly ~8–12%; larger deals use scaled fees; ⚠️ negotiable) matter at small sizes.

---
