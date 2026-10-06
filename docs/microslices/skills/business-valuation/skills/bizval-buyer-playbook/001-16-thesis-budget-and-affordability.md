---
id: skill-16-thesis-budget-and-affordability-f3306bca05
purpose: 16 thesis budget and affordability
source: src/vibey_tools/skills/plugins/business-valuation/skills/bizval-buyer-playbook/SKILL.md
requires: []
links: ["skill-17-sourcing-and-screening-db9c2cc561"]
---

## §16. Thesis, Budget and Affordability

### 16.1 Define the buyer
- **Owner-operator** (you will run it): you are buying a *job plus equity*: pay for **SDE minus a fair salary** for yourself.
- **Investor/search-fund/PE:** pay for **EBITDA after a market-rate manager** and a growth/synergy plan.
- **Strategic:** pay for synergies, but **don't pay the seller for your synergies** unless competition forces it.

### 16.2 Affordability math (use the tool)
`max_price_for_dscr(cash_flow_for_debt_service, min_dscr, apr, years, equity_pct=0.10, other_costs_pct=0.03)`.
**Example (Main Street):** median sold business: **cash flow $155,921**; buyer draws **$70,000** (placeholder) → **$85,921** available for debt service. At **DSCR 1.25**, **10% / 10 years**: max debt service **$68,737/yr**, max loan **$433,449**, max **price $467,583**, equity needed **$48,161**. At **8%**: **$509,294 (+9%)**.
**Median deal check:** price **$349,250**, costs $12,000 → **total project cost $361,250**; **10% equity = $36,125**, of which up to half can be a *full-standby* seller note ($18,062) and half **buyer cash ($18,062)**; **SBA loan $325,125 (90%)**; debt service ~$51,568/yr → **DSCR 1.67**. *Interpretation:* the median small deal is comfortably financeable; **the binding constraint for larger prices is the cash flow after your own salary and the lender's DSCR**, not the 10% down.
**Also budget:** closing costs (~3% placeholder), **working-capital needs** (inventory, payables timing), **owner's living costs** during transition, **a reserve** (3–6 months of debt service and payroll), **legal/QoE fees**.

### 16.3 Return thresholds
- **Owner-operator:** target **a cash-on-cash and income return above your next best job** (salary + 15–30% return on equity is a common aspiration, ⚠️ judgment).
- **Investor:** underwrite the **IRR/MOIC** at *your* cost of capital (§12): small private-company discount rates of **12–25%+**; `lbo()` for leveraged deals.

---
