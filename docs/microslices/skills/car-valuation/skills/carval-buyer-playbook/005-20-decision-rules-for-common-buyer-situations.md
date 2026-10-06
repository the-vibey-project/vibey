---
id: skill-20-decision-rules-for-common-buyer-situations-1b9930c7db
purpose: 20 decision rules for common buyer situations
source: src/vibey_tools/skills/plugins/car-valuation/skills/carval-buyer-playbook/SKILL.md
requires: ["skill-19-under-contract-f-i-inspection-and-closing-d175b1a228"]
links: ["skill-20a-buyer-checklists-c8e07c54ab"]
---

## §20. Decision Rules for Common Buyer Situations

### 20.1 Keep the car you have vs replace it
`repair_or_replace(vehicle_value, repair_cost, expected_extra_years, replacement_monthly_cost, current_monthly_cost, expected_other_repairs_yr)`.
**Illustration:** value $9,000; repair $2,800 (31% of value); keep 3 more years with $700/yr other repairs and $200/mo current costs → **$12,100** vs replacing at $650/mo → **$23,400**. **Keep** if the repair is **< ~50% of value**, the repair fixes a root cause, and the car is otherwise sound. **The cheapest car is usually the one you already own**, absent safety issues or chronic failures.

### 20.2 Rolling negative equity into a new loan
Avoid when possible. Options: **keep driving** until the loan balance falls below value; **pay down principal** (extra payments); **sell privately** and cover the gap with cash/a personal loan (often cheaper than financing it at car-loan rates plus fees); **refinance** to a shorter term if rates allow. **Cost of rolling $6,884 (the Q2 2026 average) at 6.35% over 70 months: +$118/month and +$8,255 total** (toolkit), because the loan principal is higher *and* the new car depreciates on a larger base.

### 20.3 EV vs gas (running cost)
`ev_vs_ice()` with 0.30 kWh/mi, 80% home charging at $0.17/kWh, 20% public at $0.45/kWh, 30 mpg gas at $4.10: **EV $0.068/mi vs gas $0.137/mi → ~$826/yr savings at 12,000 mi** (placeholder inputs). **The savings don't automatically offset a higher price** (new-EV ATP $54,813): run `tco()` for both with your numbers, **don't subtract the federal credit (ended Sept 30, 2025)**, and **check state/utility incentives, home-charging installation cost, insurance and battery warranty.**

### 20.4 Lease vs buy
See §28.2 → `carval-diligence-risk-and-ownership-economics`. Short answer: leasing wins when the **residual is high** relative to what the car will actually be worth and the **money factor is low**; buying wins when you keep the car beyond the term or the residual is low.

### 20.5 Trade timing and the "payment treadmill"
The classic trap is trading every 3–4 years while still owing more than the car is worth. Each rollover adds interest and makes the next trade harder. **Break the cycle** with a **larger down payment**, a **shorter term**, or **holding the car** until you have equity.

### 20.6 Buying from out of state
Factor **transport cost**, **sales tax and registration in your state** (you generally pay your home state's tax at registration), **return/inspection rights**, and **PPI** by a shop near the car (get a remote PPI service if needed). Compare OTD in *your* state.

---
