---
id: skill-28-ownership-economics-67f7c5c5b2
purpose: 28 ownership economics
source: src/vibey_tools/skills/plugins/car-valuation/skills/carval-diligence-risk-and-ownership-economics/SKILL.md
requires: ["skill-27-fraud-and-scam-patterns-f184046b16"]
links: ["skill-29-specialty-cases-ee0de2a1ec"]
---

## §28. Ownership Economics

### 28.1 Total cost of ownership (TCO)
`tco(price, years, miles_per_year, resale_value, apr_pct, down, loan_months, insurance_yr, fuel_cost_per_mile, maintenance_yr, registration_yr, repairs_yr, sales_tax_pct, fees)`.
**Verified example:** $31,500 car, 5 years, 12,000 mi/yr, 20% down, 6.9% over 60 months, 6% tax, $500 fees, insurance $2,000/yr, fuel $0.13/mi, maintenance $600/yr, repairs $300/yr, registration $150/yr; resale = **58.3% of price** (placeholder retention).
| Component | 5-year total | Share |
|---|---|---|
| Depreciation | $13,135 | 30% |
| Interest | $5,111 | 12% |
| Sales tax + fees | $2,390 | 5% |
| Running costs (insurance, fuel, maintenance, registration, repairs) | $23,050 | **53%** |
| **Total** | **$43,686** | **$8,737/yr · $728/mo · $0.73/mile** |
**Lessons:** (a) **insurance and fuel** dominate running costs and differ widely by model; (b) the **cheapest-to-buy car isn't necessarily the cheapest to own**; (c) **holding longer** spreads depreciation and interest over more miles; (d) **sanity-check** against published per-mile ownership costs (AAA, Edmunds, KBB) for your class.

### 28.2 Lease vs buy
**Lease math:** monthly = **depreciation fee** `(cap cost − residual)/term` + **rent charge** `(cap cost + residual) × money factor`; **APR ≈ money factor × 2,400**; tax rules vary by state.
**Verified example:** $36,000 MSRP, 58% residual ($20,880), 36 months, MF 0.0027 (**6.48% APR-equivalent**), $2,000 cap reduction, $695 acquisition fee, 6% tax → cap cost **$34,695**; depreciation fee **$383.75**; rent charge **$150.05**; **$533.80/mo pre-tax; $565.83 with tax**.
**Versus buying the same car** (36-month loan at 6.9%, $2,000 down, car worth **70% of MSRP** at month 36 per the placeholder retention curve):
| Metric | Lease | Buy |
|---|---|---|
| Monthly | **$543** | **$1,115** |
| Total cash over 36 months | $21,562 | $42,135 |
| **Net cost after resale/equity** | **$21,562** | **$16,867** |
| Net incl. 4% opportunity cost on down payments | $21,811 | $17,117 |
**Why buying won here:** the contractual **residual (58%) was below the car's likely market value (70%)**; the lessor captures that equity. **Leasing wins when:** the **residual is high** (manufacturer-subsidized), the **money factor is subsidized** (lease cash/low MF), you **change cars every 2–3 years**, you drive **within the mileage allowance**, and (business use) tax treatment helps. Experian data (Q2 2026, via a secondary summary) shows a new lease averaging about **$148/month less** than a new loan: **lower payment, no ownership.**
**Negotiate:** the **cap cost** (like a purchase price), the **money factor** (ask for the buy rate), the **residual/miles**, and **fees** (acquisition, disposition); **avoid** rolling negative equity or add-ons into the lease; **check early-termination and wear terms**; **GAP** is usually included.

### 28.3 EV vs gas running costs
`ev_vs_ice()` with 0.30 kWh/mi; 80% home charging at $0.17/kWh and 20% public at $0.45; gas car 30 mpg at $4.10/gal: **EV $0.068/mi vs gas $0.137/mi → ~$826/yr saved at 12,000 mi.**
**What the running-cost saving must overcome:** a higher purchase price (new-EV ATP **$54,813** vs industry **$50,089**), possible **faster depreciation**, **home-charger installation**, **state EV registration surcharges** (many states charge them), insurance differences, tire wear and public-charging dependence. **Federal EV credits ended Sept 30, 2025.** Run `tco()` for both with your inputs; the EV wins more often with **high mileage, cheap home electricity and low purchase prices.**

### 28.4 Repair vs replace
See §20.1 → `carval-buyer-playbook`. **Rule of thumb:** repair when the cost is **< ~50% of value**, it fixes a root cause, and the car is otherwise sound; consider **replacement** when repairs recur (>$1,500–$2,000 a year), safety is compromised, or the car is near a major-cost threshold (transmission, head gasket, rust-through) *and* worth less than the repair.

### 28.5 Warranties and extended service contracts
- **Factory warranty** (bumper-to-bumper, powertrain, battery) and **CPO** coverage: know *what's left* (by VIN) and whether it's **transferable** (some are, with fees).
- **Extended warranty (VSC) value test:** expected claim cost vs price; **reliable models** rarely repay; **luxury/complex cars** sometimes do. **Check:** exclusions, deductible, labor rate, claim approval process, **repair-shop choice**, cancellation refund, **underwriter quality**. A cheaper alternative: **self-insure** by putting the same amount into a repair fund. **Price is negotiable**; get quotes from the manufacturer and independent providers.

### 28.6 Insurance as a valuation factor
Insurance cost varies by **model, trim, ZIP, driver profile** and **repair cost/theft rates**; **get quotes before buying**; EVs/trucks/luxury can be much costlier; **higher deductibles** and **usage-based programs** reduce cost with trade-offs. For total losses, see §25.3 → `carval-seller-playbook`.

---
