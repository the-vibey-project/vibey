---
name: bizval-buyer-playbook
description: "Use when buying a company or business interest: acquisition thesis and affordability (debt capacity at DSCR 1.25, equity needed), sourcing and screening listings and CIMs, the three-number approach (value range, financeable price, walk-away), LOI terms and structure (cash at close, seller note, earnout, rollover, escrow, working-capital peg), present-value of structured offers, financing (SBA 7(a) SOP 50 10 8 and 8.1 rules, conventional/private credit, seller financing, search-fund/independent-sponsor equity, LBO return sensitivity to rates and exit multiple), due-diligence scope and red flags, closing deliverables, transition and a 100-day plan, and special cases (distressed, franchise, partner buy-in)."
---

# Company and Non-Profit Valuation: The Buyer Playbook

> **Part 4 of 9** of the *Company and Non-Profit Valuation* reference (plugin `business-valuation`), covering §16–§20. Sibling skills: `bizval-concepts-standards-and-market-structure` (§0–§4), `bizval-market-analysis-and-timing` (§5–§9), `bizval-valuing-a-private-company` (§10–§15), `bizval-seller-playbook` (§21–§25), `bizval-diligence-startups-public-and-disputes` (§26–§30), `bizval-nonprofit-valuation-and-transactions` (§31–§34), `bizval-nonprofit-financial-health-and-impact` (§35–§38), `bizval-reference` (§39–§43). Code: `scripts/bizval.py` (`max_price_for_dscr`, `sba_sources_uses`, `deal_pv`, `lbo`, `dscr`, `loan_payment`).
>
> **Currency:** Procedures are stable; rates and SBA rules are **October 2026** and changing. Example loan rates are placeholders.

> **⚠️ Scope.** Educational; not legal, tax or financing advice. **Hire an attorney and a CPA/QoE provider for any acquisition.** SBA and lender rules should be read from the current SOP and the lender's term sheet.

> **The three ideas:**
> 1. **⚠️ You buy cash flow that survives the seller.** Value the *transferable* earnings; use due diligence to reprice, not just to confirm (§20).
> 2. **⚠️ Financeability caps price, whatever the "value."** In the toolkit, a business with $85,921 of cash flow after a buyer salary supports a maximum **~$467,600 price** at a 10% loan rate (10 years, DSCR 1.25), **~$509,300 at 8%**: **each point of loan rate ≈ 4% of price** (§16, §19).
> 3. **⚠️ Compare offers on present value and certainty, not headline.** A $5.25M structured offer (cash $3.0M + note + earnout + rollover + escrow) had a **seller-side PV of ~$4.60M (87.5%)**; as a buyer, structure is how you bridge a valuation gap *and* keep the seller aligned, but over-reliance on contingent pay invites disputes (§18).

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

## §17. Sourcing and Screening

### 17.1 Channels
**Broker listings** (BizBuySell and others; **broker works for the seller**), **proprietary outreach** (direct mail/email to owners in your niche), **investment-bank/advisor processes** (LMM+), **industry networks**, **search-fund/independent-sponsor platforms**, **marketplaces for online/SaaS businesses**, **distressed/bankruptcy sales**.

### 17.2 Screening metrics (first pass)
| Metric | What to ask |
|---|---|
| **Price ÷ SDE/EBITDA** | Compare to §11 comps for size and quality |
| **SDE margin / EBITDA margin** | Plausible for the sector? |
| **Owner's role** | Hours, relationships, skills required: *can you do it?* |
| **Customer concentration** | **Top customer share**; contract terms |
| **Revenue quality** | Recurring %, cohort retention, backlog |
| **Trend** | 3–5 years and TTM; **why is the owner selling now?** |
| **Capital needs** | Capex, working capital, licensing |
| **Lease/location** | Assignment, term, rent vs market |
| **Employees** | Key people, wage levels |
| **SBA eligibility** | Industry, size, ownership, financing path (§19) |
**CIM red flags:** pro forma earnings with no history; "owner works 10 hours/week" yet **sales depend on owner**; vague add-backs; revenue concentrated in one customer; **declining TTM**; **a price far above comps** (**listings with unrealistic asks often never sell**); resistance to sharing tax returns or bank statements; **cash-heavy** businesses with no controls.

### 17.3 First conversations
**NDA** first; ask for **3–5 years of tax returns and financials, TTM P&L, A/R and A/P aging, top-10 customer list (anonymized), lease, org chart, owner's role, reason for sale.** **Verify with tax returns and bank statements** before spending on diligence.

---

## §18. Value, Offer and LOI

### 18.1 The three numbers
1. **Value range** (from §10–§15, on normalized earnings).
2. **Financeable price** (from §16.2 and your equity).
3. **Walk-away**: the **lower** of (value-range high end plus any justified synergy premium) and (price at which your minimum return/DSCR fails). **Write it down. Don't revise it upward in the negotiation.**

### 18.2 Structure as a bridge: and its price
`deal_pv()` values the *seller's* package at their required return.
**Example offer:** headline **$5.25M** = **$3.0M cash** + **$1.0M seller note (6%, 5 years)** + **$0.5M earnout (40% probability, year 2)** + **$0.5M rollover (25% illiquidity haircut)** + **$250k escrow (85% release)** → **seller PV ≈ $4.60M (87.5% of headline; 57% in cash at close).** An **all-cash $4.3M** bid is worth **$4.3M**: a seller may rationally prefer **$4.3M cash** if they doubt the earnout or your credit.
**Use structure for:** (a) a **valuation gap** (earnout on the uncertain part), (b) **seller alignment/transition** (note, rollover), (c) **SBA equity** (standby note), (d) **risk sharing** (escrow). **Don't use it** to disguise a low offer; sellers and advisors compute PV.

### 18.3 LOI checklist (usually non-binding except exclusivity, confidentiality, costs)
| Term | Notes |
|---|---|
| **Price, form and basis** | Cash-free, debt-free; allocation to assets; **earnout/seller note** terms |
| **Working-capital peg** | Normalized level; true-up mechanics (§14.3) |
| **Exclusivity (no-shop)** | 45–90 days typical; **tie to diligence progress** |
| **Financing contingency** | Lender, amount, timeline; **proof of funds** |
| **Diligence scope and access** | Financial, tax, legal, HR, IT, customers (late-stage calls with consent) |
| **Employees/key people** | Retention/offer letters; **seller transition period (6–12 months)** |
| **Non-compete/non-solicit** | Duration, geography; **enforceability varies by state** |
| **Lease/permits** | Assignment, landlord consent |
| **Escrow/holdback, indemnity** | Size (e.g., 5–15% placeholder), duration, caps, baskets |
| **R&W insurance (larger deals)** | Retention, exclusions |
| **Closing conditions and timeline** | Third-party consents, key customer retention |
| **Costs** | Who pays what; **break fee** if any |

### 18.4 Earnout design (if used)
Define the **metric** (revenue, gross profit, EBITDA), the **accounting policies**, **operating covenants** (control of the business post-close), **acceleration** on sale, **dispute resolution**, **caps**, **timing**. **Earnouts are the most litigated deal term;** prefer **revenue/gross-profit** metrics (harder to manipulate) over EBITDA.

### 18.5 Negotiating price
- **Open** at the low end of a *defensible* range, citing **normalized earnings and comps**; **concede** only for **structure** or **risk reduction**; **retrade** on **verified diligence findings** (not tactics).
- **Know the seller's alternatives** (other buyers, tax-driven timing); **their after-tax proceeds** (§24) matter more than your headline.

---

## §19. Financing

### 19.1 SBA 7(a) (Main Street and small LMM)
| Rule | Detail (verify the current SOP and lender policy) |
|---|---|
| **Max loan** | **$5M**; reported cumulative 7(a)+504 limit **$10M** from July 4, 2026 (⚠️ single source) |
| **Equity injection** | **≥10% of total project cost** (price + fees + working capital) for a complete change of ownership (SOP 50 10 8, eff. June 1, 2025) |
| **Seller note as equity** | Counts **only if on full standby (no principal or interest) for the life of the loan and ≤50% of the required injection**; **SOP 50 10 8.1 (Oct 1, 2026)** reportedly caps **seller standby + outside investor equity at 50% combined** |
| **Term** | **≤10 years** amortization for change of ownership; real estate up to 25 |
| **Underwriting** | **DSCR ≥1.25** (lenders often higher); credit-elsewhere narrative; **independent valuation in some cases (8.1)**; **tax returns and historical earnings** |
| **Guarantee** | **Owners ≥20% guarantee**; **sellers who retain any equity must guarantee** for a period |
| **Eligibility** | **U.S. ownership/citizenship rules tightened** (March 2026 notice); industry restrictions |
| **Pricing** | Prime (**7.00%**) + spread (maximum varies by size; ~**10%** at the top, verify) + guaranty/packaging fees |
| **Process** | LOI → lender term sheet → SBA Form 1919/1920 package → appraisal/valuation/ environmental if needed → closing (**60–120 days** typical) |

### 19.2 Other capital
- **Conventional bank/term loans** (collateral-heavy, 5–7 years), **ABL/inventory/equipment financing**, **SBA 504** (real estate/equipment), **private credit/unitranche** (middle market), **seller financing** (flexible; **rate, term, subordination, security, covenants**), **earnout**, **rollover equity**, **search-fund/independent-sponsor equity**, **ROBS (retirement rollover)** (⚠️ high risk; get specialized advice).
- **Equity partners:** align on **governance, drag/tag, preferred returns, exit timing, information rights**.

### 19.3 Leverage, rates and returns (`lbo()`; simplified model)
Entry **7.0× TTM EBITDA**, **4.5× debt**, 6% growth, exit **7.0×**, 5 years:
| Debt cost | MOIC | IRR |
|---|---|---|
| 6% | 2.88× | 23.5% |
| 8% | 2.77× | 22.6% |
| 10% | 2.65× | 21.5% |
| 12% | 2.52× | 20.3% |
**One turn lower exit multiple (6.0×) at 10% debt → IRR 16.6%.** *Lessons:* **(1) the exit multiple matters more than the coupon in this range;** (2) **leverage magnifies** rate and multiple risk; (3) ⚠️ **the simplified model overstates cash conversion** (real LBOs carry fees, working capital, add-on spending and covenants): use it for relative sensitivity only.

---

## §20. Due Diligence, Closing and Transition

### 20.1 Diligence scope
| Workstream | Key questions |
|---|---|
| **Financial/QoE** | Earnings quality, add-backs, working-capital peg, debt-like items, cash proof (§10.3) |
| **Commercial** | Customer calls, **churn, concentration, pricing**, competition, market size |
| **Legal** | Entity, contracts (assignment/**change of control**), litigation, IP chain of title, licenses, compliance |
| **Tax** | Federal/state/sales/payroll tax compliance; **structure** (asset vs stock; §24); **successor liability** |
| **HR** | Key employees, wage/hour, misclassification, benefits, unions, **non-competes** |
| **IT/cyber/data** | Systems, security incidents, privacy compliance, data ownership |
| **Operational** | Equipment condition, capacity, supply chain, safety |
| **Real estate/environmental** | Lease terms, zoning, Phase I |
| **Insurance** | Coverage, claims history |
| **Regulatory** | Licenses, permits, industry-specific approvals |
Details and red flags: §26–§27 → `bizval-diligence-startups-public-and-disputes`.

### 20.2 Using diligence to reprice
Classify each finding: **(a) price** (quantified adjustment), **(b) structure** (escrow, indemnity, earnout), **(c) fix before close** (condition), **(d) walk**. **Retrade only on documented facts**; keep a **findings log with dollar impact** and **seller responses**.

### 20.3 Definitive agreement and closing
**Reps and warranties** (financials, taxes, compliance, litigation, IP, employees); **indemnity** (caps, baskets, survival periods; **fraud carve-outs**); **escrow/holdback**; **working-capital true-up**; **closing deliverables** (assignments, consents, estoppels, releases, payoff letters, bills of sale, employment/consulting agreements, non-compete, **lease assignment**); **funds flow**; **insurance** (including tail coverage); **post-closing covenants**.

### 20.4 Transition and the first 100 days
Retain **key employees and customers** (communicate early and personally), **seller transition** (training, introductions), **systems access**, **cash controls**, **KPIs dashboard**, **quick wins**, **no big changes for 90 days** unless required, **track earnout metrics**, **document processes**.

### 20.5 Special cases
- **Distressed/bankruptcy purchase:** often asset purchases free of many liabilities (§363 sales); speed and legal risk are high; **cash buyers** have leverage.
- **Franchise resale:** franchisor approval, transfer fees, **FDD** review, territory rights.
- **Partner buy-in/minority interests:** **minority and marketability discounts** (§14), governance protections, buy-sell terms.
- **Buying real estate with the business:** separate valuation; **sale-leaseback** options.

---

## §20A. Buyer Checklists

**Before offers:** [ ] thesis [ ] financeable price (§16.2) [ ] normalized earnings and value range [ ] walk-away written [ ] advisors (attorney, CPA/QoE) [ ] proof of funds.
**LOI:** [ ] price/structure PV-tested [ ] working-capital peg [ ] exclusivity tied to progress [ ] financing and diligence contingencies.
**Diligence:** [ ] QoE [ ] customers [ ] legal/tax/HR/IT [ ] lease [ ] findings log priced [ ] repricing/walk decision.
**Closing:** [ ] R&W and indemnity [ ] consents [ ] funds flow [ ] transition plan [ ] insurance [ ] day-1 communications.
