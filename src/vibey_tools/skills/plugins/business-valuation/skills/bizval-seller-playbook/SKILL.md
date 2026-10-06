---
name: bizval-seller-playbook
description: "Use when selling or planning to sell a company: exit readiness (3-5 year runway, clean books, sell-side QoE, owner dependence, concentration, legal clean-up), valuation expectations and why asks fail, choosing advisors and process (broker vs banker, fees, auction vs negotiated, teaser/CIM/data room), comparing LOIs on after-tax, risk-adjusted present value, structure (asset vs stock with a verified $5M example, earnouts, seller notes, rollover, escrows), taxes (installment sale, allocation, QSBS under OBBBA with verified 3/4/5-year numbers, state tax, estate/charitable planning, ESOP), alternatives (MBO, ESOP, family succession, recapitalization, wind-down), and post-sale obligations."
---

# Company and Non-Profit Valuation: The Seller Playbook

> **Part 5 of 9** of the *Company and Non-Profit Valuation* reference (plugin `business-valuation`), covering §21–§25. Sibling skills: `bizval-concepts-standards-and-market-structure` (§0–§4), `bizval-market-analysis-and-timing` (§5–§9), `bizval-valuing-a-private-company` (§10–§15), `bizval-buyer-playbook` (§16–§20), `bizval-diligence-startups-public-and-disputes` (§26–§30), `bizval-nonprofit-valuation-and-transactions` (§31–§34), `bizval-nonprofit-financial-health-and-impact` (§35–§38), `bizval-reference` (§39–§43). Code: `scripts/bizval.py` (`deal_pv`, `asset_vs_stock`, `qsbs_exclusion`, `ev_to_equity`, `apply_discounts`).
>
> **Currency:** Procedures are stable; tax and market data **October 2026**. Tax examples are **stylized**.

> **⚠️ Scope.** Educational; **not tax, legal or investment advice.** A sale is irreversible and heavily tax- and structure-dependent: **engage an M&A attorney, a CPA with transaction experience, and (for LMM+) an investment banker before signing an LOI.**

> **The three ideas:**
> 1. **⚠️ Your net, after-tax, risk-adjusted proceeds, not the headline, is the number.** In a stylized $5M sale, **structure alone shifted ~$170,000 of tax** (asset vs stock) and **a structured $5.25M headline was worth ~$4.6M in present value** (§22, §24).
> 2. **⚠️ You sell a transferable business, not yourself.** Buyers discount owner dependence, concentration and messy books heavily. The best price-improvement projects are usually **3–5 years of preparation**, not negotiating tactics (§21).
> 3. **⚠️ Sell on strength.** A rising trailing twelve months, clean financials and competitive process beat waiting for a better market; volume is down ~10% and **quality closes** (§21, §9.4 → `bizval-market-analysis-and-timing`).

---

## §21. Exit Readiness

### 21.1 Define the goal
**Net proceeds needed**, timing, role after sale, legacy (employees, customers), risk tolerance for earnouts/rollover. **Compare with the value of keeping** (the PV of the owner's income stream plus eventual sale): selling at 2.7× SDE means giving up a ~37% annual cash yield on price (before taxes and replacement labor).

### 21.2 Readiness workplan (3–5 years ideal; 12–18 months minimum)
| Area | Actions | Why buyers care |
|---|---|---|
| **Financials** | **Monthly closes, accrual-basis or reconciled financials, reviewed/audited statements** where feasible; **sell-side QoE**; separate personal expenses | Clean books raise confidence, speed and SBA eligibility; they directly affect the multiple |
| **Owner dependence** | Document processes; **delegate sales and key relationships**; hire/promote a manager; train a successor | Dependence reduces earnings (replacement labor) and the multiple |
| **Customers** | Reduce **top-customer share** (<15–20% each is a common comfort level, ⚠️ heuristic); **long-term contracts**; recurring revenue | Concentration is the most common valuation haircut |
| **Earnings trend** | Don't deplete maintenance, cut marketing, or defer capex to "boost" TTM; **buyers detect it** | A rising TTM beats a one-time spike |
| **Legal** | Clean cap table; **contracts assignable**; IP assignments; licenses/permits; employment agreements; resolved litigation | Closing risk and indemnity |
| **Tax** | Tax filings current; **entity structure** (S/C/LLC) reviewed for exit; consider **QSBS** (C-corps, §24.3) | Net proceeds |
| **Lease/real estate** | Assignable, term, **market rent** (separate real estate from operating business) | Financing and value |
| **Team** | **Retention agreements** for key people | Buyers pay for the team |
| **Data room** | Organize 3–5 years of documents before launch | Speed; fewer retrades |

### 21.3 Timing
- **Sell on a rising TTM** and when you have **at least 3 years of clean financials**; avoid launching right after a down year unless you can explain it.
- **Don't wait for the macro.** The Fed hiked to **3.75–4.00%** and the 10-year is **~5.3%**; financing is costlier, **volume is down ~10%** and multiples are flat, so *the main costs of waiting are earnings erosion and owner fatigue*, not a predictable price decline (§9).
- **Tax-law timing:** much of the "sell before the tax increase" urgency eased because **TCJA brackets were made permanent**, while **QSBS is more generous for stock issued after July 4, 2025** (§24). Confirm with your CPA.

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

## §23. Advisors and Process

### 23.1 Choosing an advisor
| Size | Advisor | Notes |
|---|---|---|
| **Main Street (<~$1M SDE)** | **Business broker** (IBBA members) | Success fee; **check closing record in your sector**; understand **exclusivity, tail periods, who pays costs** |
| **LMM ($1–10M+ EBITDA)** | **M&A advisor/investment bank** | Retainer + success fee (scaled formulas); **run a competitive process**; contacts in PE/strategic |
| **Larger** | Investment bank | Fairness/valuation analysis, process |
**Also:** M&A **attorney** (essential), **CPA/tax advisor**, **wealth/estate planner**, **QoE provider**.

### 23.2 Process (typical 6–9 months; Main Street median reported ~150–170 days to close)
1. **Preparation** (QoE, CIM, data room, buyer list)
2. **Marketing** (teaser, NDAs, CIM, Q&A)
3. **IOIs** (indications of interest) → **management meetings**
4. **LOIs** (compare; negotiate; **exclusivity**)
5. **Confirmatory diligence** (expect requests, retrades)
6. **Definitive agreements** and **closing**
**Auction vs negotiated:** **Competitive** processes lift price and terms when there are multiple credible buyers; **negotiated** deals save time and confidentiality when there's a natural buyer. **Confidentiality:** use NDAs, **stage-gated disclosure** (don't reveal customers or financial detail until late), and a story for employees.

### 23.3 Comparing LOIs
| Criterion | Questions |
|---|---|
| **After-tax PV** | Price components, taxes, timing (use §22.2 and §24) |
| **Certainty** | Financing (SBA? lender commitments, proof of funds), diligence scope, conditions, **track record** |
| **Speed** | Time to close; exclusivity length |
| **Structure** | Seller note security/subordination, earnout metric and control, escrow size/duration, **rollover terms** |
| **Post-close** | Your role, non-compete, employee treatment |
| **Retrade risk** | Buyer's reputation; diligence "gotchas" |
**Heuristic:** a buyer with **SBA financing** needs ≥10% equity, **standby seller note limits** and a **valuation/DSCR test**: *probe* feasibility early (§19 → `bizval-buyer-playbook`).

---

## §24. Structure and Taxes (stylized; not tax advice)

### 24.1 Asset vs stock (S-corp/pass-through example)
**Price $5.0M; stock basis $0.8M; ordinary-income recapture $0.6M; inventory/AR ordinary $0.4M; federal LTCG 20% + NIIT 3.8% + state 5%; ordinary 37% + NIIT + state:**
| | Stock sale | Asset sale |
|---|---|---|
| Seller tax | **$1,209,600** | **$1,379,600** |
| Net to seller | $3,790,400 | $3,620,400 |
**Seller's extra tax in an asset deal: $170,000 (3.4% of price).** **Buyer's step-up** (15-year amortization of $4.2M at 25% tax, 12% discount rate) has a **PV of ~$477,000**: *the buyer gains more than the seller loses*, so a **gross-up** is negotiable (and **100% bonus depreciation**, permanent for property acquired after Jan 19, 2025, can make equipment step-ups worth more). **Alternatives that give buyers a step-up with less seller cost:** **338(h)(10)/336(e) elections**, **F-reorganization** (S-corps), **LLC interest sales**: *structure these with a transaction tax attorney.*
**C-corp sellers** face **double tax** on asset sales; **QSBS** or stock sales are the usual paths.

### 24.2 Other tax and accounting items
- **Allocation of purchase price** among asset classes (**Form 8594**): buyer and seller interests conflict; **negotiate it in the LOI**.
- **Installment sale** (seller notes/earnouts): defers recognition; **interest and risk**.
- **Earnouts:** treatment as purchase price vs compensation; **tax and timing** vary.
- **Non-compete allocation:** ordinary income to the seller; amortization to the buyer.
- **State taxes, transfer taxes, sales tax on tangible assets.**
- **Estate/gift planning:** **gifting shares before a letter of intent** (to trusts) can reduce estate tax, but **post-LOI transfers draw IRS scrutiny** (step-transaction, assignment of income); consult counsel early.
- **Charitable planning:** **donor-advised funds/CRTs** before closing; **2026 rule changes**: **0.5% AGI floor for itemizers, 35% value cap for top-bracket donors, new $1,000/$2,000 non-itemizer deduction** (§35).
- **ESOP:** **§1042** deferral for C-corp sellers, leveraged ESOP financing; requires **independent annual valuation** (§25).

### 24.3 QSBS (Section 1202): verified arithmetic
Stock **issued after July 4, 2025**: exclusion **50% at 3 years, 75% at 4 years, 100% at 5**; **cap the greater of $15M or 10× basis**; gross-asset test **$75M**; **non-excluded gain on 3–4 year holds is taxed at up to 28% plus 3.8% NIIT**; stock **issued on/before July 4, 2025** keeps the **old rules** ($10M cap; 100% only at 5 years).
**On a $12M gain:**
| Holding period | Exclusion | Federal tax | Effective rate |
|---|---|---|---|
| < 3 years | 0% | $2,856,000 | 23.8% |
| 3 years | 50% | $1,908,000 | 15.9% |
| 4 years | 75% | $954,000 | 8.0% |
| **5 years** | **100%** | **$0** | **0%** |
**Old-rule stock held 4 years:** no exclusion (tax $2,856,000). **A $40M gain at 5 years:** **$15M excluded, $25M taxable.** **QSBS applies only to qualifying C-corporation stock acquired at original issuance in an active business with ≤ $75M ($50M for older stock) in gross assets at issuance** (plus other tests): *verify eligibility with counsel before relying on it.*

---

## §25. Alternatives, Special Sellers and After the Sale

### 25.1 Alternatives to a third-party sale
| Option | When it fits | Watch-outs |
|---|---|---|
| **Management buyout (MBO)** | Strong team | Valuation conflict; financing; **seller note** |
| **ESOP** | Employee-ownership, tax-advantaged liquidity, culture | Complexity, **independent valuation**, leverage, **fiduciary obligations**; price may be below strategic bids |
| **Family succession** | Legacy | **Fairness among heirs**, **discounts**, **gift/estate tax**, governance |
| **Partial sale/recap** | Take chips off the table | **Minority discount**, governance, exit expectations |
| **Merge with a competitor/roll-up** | Scale | Culture, earnout/rollover risks |
| **Wind-down/liquidation** | No buyer | **Liquidation value**; employee/customer obligations |
| **Distressed sale (§363/ABC)** | Insolvent | Speed, creditor priorities |

### 25.2 After the sale
**Transition period** (6–24 months), **non-compete/non-solicit**, **earnout management** (monitor metrics, keep records), **indemnity claims** (survival periods), **seller note collection**, **tax payments and estimated taxes**, **portfolio planning**, **identity and purpose**. **Keep copies of the definitive agreement, schedules, closing statements and tax allocations.**

---

## §25A. Seller Checklists

**18–36 months out:** [ ] clean monthly financials [ ] QoE [ ] reduce owner dependence and concentration [ ] key-employee retention [ ] legal/tax clean-up [ ] advisors.
**Launch:** [ ] range and floor [ ] CIM and data room [ ] buyer list [ ] NDA process [ ] confidentiality plan.
**LOI:** [ ] after-tax PV comparison [ ] certainty of funds [ ] structure acceptable [ ] exclusivity limited.
**Close:** [ ] working-capital peg [ ] escrow and indemnity terms [ ] allocation (Form 8594) [ ] employment/transition [ ] payoff letters [ ] funds flow [ ] tax plan.
