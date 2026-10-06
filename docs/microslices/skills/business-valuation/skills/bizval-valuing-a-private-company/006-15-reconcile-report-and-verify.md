---
id: skill-15-reconcile-report-and-verify-0907075343
purpose: 15 reconcile report and verify
source: src/vibey_tools/skills/plugins/business-valuation/skills/bizval-valuing-a-private-company/SKILL.md
requires: ["skill-14-discounts-premiums-and-the-bridge-to-equity-7c4d0c979d"]
links: []
---

## §15. Reconcile, Report and Verify

### 15.1 Reconcile
| Method | Result (example) | Weight |
|---|---|---|
| Market (regression-adjusted multiple × EBITDA) | $X | e.g., 50% |
| Income (DCF, with grid) | $Y | e.g., 30% |
| Capitalized earnings | $Z | e.g., 20% |
| Asset floor | $F | Floor |
**Rules:** the **range** matters more than the point; **explain differences** (growth, multiple, discount rate); **cap the answer by financeability** (§19).

### 15.2 Sanity checks
1. **Implied multiples** (EV/EBITDA, EV/revenue, price/SDE) vs comps (§11).
2. **Implied buyer return** (`implied_discount_rate`) vs required return.
3. **DSCR and payback:** can a buyer finance it (§19)? **Payback** ≈ price ÷ owner-adjusted cash flow.
4. **Revenue/employee, margin vs peers.**
5. **What must be true?** (growth, margins, retention): *are they plausible?*

### 15.3 Report: confidence statement template
*"Informal opinion of value (not an appraisal): enterprise value of $X–$Y (most likely about $Z) on a cash-free, debt-free basis as of [date], under [standard] and [premise], for [purpose]. Based on normalized [SDE/EBITDA] of $[ ] (add-backs verified: [ ]), market multiples of [ ]× adjusted for size/growth/recurring/concentration, and a DCF at [r]% with a terminal growth of [g]% (TV = [ ]% of EV). Largest uncertainties: [owner dependence / concentration / rates]. A ±1-point discount rate moves value by ±[ ]%; a ±1 turn of multiple by ±[ ]%."*

### 15.4 Tool calls
```python
import bizval as bv
s = bv.sde(net_income=..., owner_comp=..., interest=..., depreciation_amort=..., one_time_expenses=..., personal_expenses=..., one_time_income=...)
acc = bv.quality_weighted_addbacks([(amt, probability), ...])
model = bv.fit_multiple_model(deals_df)                  # ev, ebitda($M), growth, margin, recurring, top_customer
pred  = bv.predict_multiple(model, ebitda=3.0, growth=0.07, margin=0.16, recurring=0.4, top_customer=0.2)
ke = bv.capm_cost_of_equity(rf=0.056, erp=0.05, beta=1.1, size_premium=0.02, company_specific=0.02)
r  = bv.wacc(ke, cost_debt_pre_tax=0.10, debt_weight=0.30, tax_rate=0.25)
d  = bv.dcf(fcff_list, r, terminal_growth=0.03); grid = bv.dcf_sensitivity(fcff_list, [r-.02, r, r+.02], [.02, .03, .04])
adj = bv.apply_discounts(value, dlom_pct=25, key_person_pct=10)
bridge = bv.ev_to_equity(ev, debt=..., cash=..., debt_like=..., nwc_shortfall=...)
```
