---
id: skill-20-decision-rules-for-common-buyer-situations-162aceda78
purpose: 20 decision rules for common buyer situations
source: src/vibey_tools/skills/plugins/home-valuation/skills/homeval-buyer-playbook/SKILL.md
requires: ["skill-19-under-contract-the-due-diligence-timeline-7a1dd26ae0"]
links: ["skill-20a-buyer-checklists-a0bd1efc7d"]
---

## §20. Decision Rules for Common Buyer Situations

### 20.1 Rent vs buy (opportunity-cost aware)
`hv.rent_vs_buy(price, down_pct, rate_pct, tax_rate_pct, insurance_annual, maintenance_pct, monthly_rent, years, appreciation_pct, rent_growth_pct, invest_return_pct)`.
**Verified illustration:** $429,100 home, 10% down, 7.28%, taxes 0.9%, insurance $3,057, maintenance 1%, rent $2,400 (rent/price ≈ 0.56%/mo), rent growth 3%, investment return 6%:
| Years | Appreciation | Buy net worth | Rent net worth | Winner |
|---|---|---|---|---|
| 3 | 3% | $57,196 | $109,866 | Rent |
| 7 | 3% | $132,012 | $183,971 | Rent |
| 7 | 5% | $201,976 | $183,971 | **Buy** |
| 15 | 3% | $326,781 | $333,542 | ≈ even |
At these inputs the **break-even is a ~15-year horizon at 3% appreciation, or ~4.5–5% annual appreciation over 7 years.** ⚠️ **Everything depends on your rent-to-price ratio:** at higher ratios (rent ≥ 0.8% of price) buying wins sooner. The model ignores tax deductions (itemizing), tax on investment gains, and non-financial value (stability, control). Run *your* numbers; do not repeat a headline.

### 20.2 Buy now or wait?
- **Waiting wins if:** you can't carry the payment with reserves; you may move in <5 years (transaction costs ~6–10% round trip); your market is *falling* (regime §9.1) and you're not forced to move.
- **Buying now wins if:** you will stay 8+ years; you have buyer's-market leverage (credits, buydown, stale listings); renting costs are rising; you can refinance later if rates fall *and* can survive the current payment.
- **Never** buy because "rates will fall" or "prices will surge"; buy because the all-in cost and the house make sense at today's rate.

### 20.3 New construction
Builder incentives (buydowns, closing credits) are often stronger than resale-seller concessions, **but** (a) the incentive may be built into the price; (b) you still need an **independent inspection** (pre-drywall and final); (c) appraisals can come in below price if the builder's incentives aren't supported by comps; (d) read the warranty and what the builder's lender requires.

### 20.4 Fixer-uppers
Underwrite **price + rehab × (1.15–1.25 contingency) + carrying costs + permits** vs *after-repair value* (§15; use renovated comps). Renovation loans (e.g., FHA 203(k), Fannie Mae HomeStyle) fund purchase + rehab. Get **contractor bids before removing contingencies.** Verify permits and that the finished product is saleable.

### 20.5 Relocating or buying remotely
Hire **local** representation and inspection; insist on a **live video walkthrough** plus a trusted local to attend; verify flood, noise, commute and neighborhood by independent data (§17.3); keep the inspection contingency.

### 20.6 First-time buyers
Research state **housing finance agency** programs (down-payment assistance, credit certificates) and their income/price caps; evaluate FHA vs conventional-3%-down total cost (PMI/MIP differences); keep reserves.

---
