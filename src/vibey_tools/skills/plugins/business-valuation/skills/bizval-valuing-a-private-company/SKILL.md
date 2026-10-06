---
name: bizval-valuing-a-private-company
description: "Use when valuing a private operating company: normalizing earnings (SDE, adjusted EBITDA, add-back evidence, quality of earnings, owner compensation, run-rate vs actual), the market approach (guideline transactions, choosing the multiple basis, size/growth/margin/recurring/concentration adjustments, a regression of multiples), the income approach (FCFF, CAPM build-up and WACC with Oct 2026 inputs, terminal value and its cross-checks, sensitivity, capitalization of earnings, implied discount rate), the asset approach, discounts and premiums (minority, DLOM, key-person, concentration), the EV-to-equity bridge, reconciliation, and a sandbox-verified worked example with scripts/bizval.py (regression recovers the true multiple function: 1.7% median EV error vs 16.4% for a median multiple and 12.1% for a size-band median)."
---

# Company and Non-Profit Valuation: Valuing a Private Company

> **Part 3 of 9** of the *Company and Non-Profit Valuation* reference (plugin `business-valuation`), covering §10–§15. Sibling skills: `bizval-concepts-standards-and-market-structure` (§0–§4), `bizval-market-analysis-and-timing` (§5–§9), `bizval-buyer-playbook` (§16–§20), `bizval-seller-playbook` (§21–§25), `bizval-diligence-startups-public-and-disputes` (§26–§30), `bizval-nonprofit-valuation-and-transactions` (§31–§34), `bizval-nonprofit-financial-health-and-impact` (§35–§38), `bizval-reference` (§39–§43). Code: `scripts/bizval.py`, `scripts/test_bizval.py`.
>
> **Currency:** Method is stable. Inputs (risk-free rate, ERP, multiples) are **October 2026** and change monthly; every default in the toolkit is a **placeholder**.

> **⚠️ Scope.** An informal valuation for decision support, **not a formal valuation, fairness opinion or tax appraisal**. The worked example (§15) uses **synthetic data with known truth**; real markets are noisier and the regression is correctly specified there, so **expect 2–3× larger errors** in practice.

> **The three ideas:**
> 1. **⚠️ Normalize before you multiply.** A 3.0× multiple on the wrong earnings figure is a wrong price. Buyers accept **documented, non-recurring, non-operating** add-backs and haircut everything else: in the example, **only $17,500 of $35,000 claimed add-backs** survived quality weighting (§10).
> 2. **⚠️ Multiples are regressions in disguise.** The "industry multiple" hides size, growth, margin, recurring revenue and concentration. A simple log-multiple regression recovered the true drivers and cut the median EV error from **16.4% (median multiple)** and **12.1% (size-band median)** to **1.7%** in the tested market (§11).
> 3. **⚠️ DCF is a leveraged opinion on two numbers: the discount rate and terminal value.** In the example, **terminal value is 65% of EV** and a **1.3-point lower discount rate raises EV 15.5%**. Always show the sensitivity grid and the implied exit multiple (§12).

---

## §10. Normalizing Earnings

### 10.1 Which earnings?
| Measure | Definition | Used for |
|---|---|---|
| **SDE (Seller's Discretionary Earnings)** | Pre-tax earnings + owner's total compensation + interest + D&A + non-recurring and discretionary/personal items; **earnings to one full-time owner-operator** | **Main Street** (price ÷ SDE) |
| **Adjusted EBITDA** | EBITDA + normalizing adjustments, **after a market-rate replacement for the owner's work** | Lower-middle and middle market |
| **Free cash flow (FCFF)** | EBITDA − taxes on EBIT − capex − Δ net working capital | DCF |
| **Run-rate / pro forma** | Adjusted for known changes (new contract, cost cut) | Negotiation; **buyers discount it heavily** |
**SDE → EBITDA:** `EBITDA ≈ SDE − fully loaded replacement manager cost`. A business with **$202,000 SDE** and a **$75,000** replacement manager has **~$127,000 EBITDA**: it belongs to a different buyer pool and a different multiple.

### 10.2 Add-back evidence ladder
| Evidence | Accepted? |
|---|---|
| **Documented, one-time, third-party-verifiable** (legal settlement invoice, storm repair) | **Yes (high probability)** |
| **Owner personal expenses run through the business** with receipts and tax filings | Often (verify against tax returns) |
| **Owner compensation above market** | Yes, but **replace the owner's labor** (§10.1) |
| **"One-time" expenses that recur** (every year) | **No** |
| **Estimated** future savings; **unpaid family labor**; **cash not reported** | Rarely: unreported cash is not earnings a buyer or lender can underwrite |
| **Related-party rent/pricing at non-market terms** | Adjust to market (up *or* down) |
**Tool:** `quality_weighted_addbacks([(9000,0.9),(14000,0.5),(12000,0.2)])` → **$17,500 accepted of $35,000 claimed**. With a $179,000 base before add-backs (net income $60k + owner comp $95k + interest $8k + D&A $22k − one-time income $6k), **claimed SDE is $214,000, quality-weighted SDE ~$196,500, and SDE with no add-backs $179,000**: a **~$17,500 (8%) swing, which at 2.7× is ~$47,000 of price**.

### 10.3 Quality of earnings (QoE) checklist
- **Revenue:** cutoff, deferred revenue, **customer concentration**, **churn/cohorts** (recurring revenue), pricing vs volume, one-time projects.
- **Margins:** gross margin by product/customer; **owner doing the selling or production**; vendor concentration.
- **Costs:** **maintenance vs growth capex**, deferred maintenance, **under-paid staff** (replacement wages), related-party items, **tax compliance** (payroll, sales tax, worker classification).
- **Working capital:** seasonality, DSO/DPO/inventory, **normalized peg** (§14.3).
- **Cash proof:** **bank statements ↔ tax returns ↔ financials** reconcile; **accrual vs cash basis**; sales tax filings; POS/ERP data.
- **Time:** use **3–5 years** and **TTM**; a **weighted average** (`weighted_average_earnings([100k,120k,150k],[1,2,3]) = $131,667`) for fluctuating earnings; **don't average away a structural decline**.

### 10.4 Transferability tests (valuation drivers that aren't in the P&L)
Owner role (sales, technical, relationships), **key employees** (retention agreements), **customer contracts** (assignable, change-of-control terms), **licenses/permits**, **lease** (assignable, term, rent vs market), **suppliers**, **brand/IP** (ownership chain), **systems/documentation**, **regulatory exposure**. Each failed test should reduce earnings, the multiple or both (§14).

---

## §11. Market Approach

### 11.1 Guideline transactions
- **Sources:** BizBuySell (Main Street), **DealStats/Pratt's Stats**, **GF Data** (PE-backed middle market), PitchBook/Capital IQ, **IBBA Market Pulse**, broker comps; **public companies** (Damodaran data, Capital IQ) only as context with size/liquidity adjustments.
- **Select comps by:** industry, **size (revenue/EBITDA ±50%)**, geography, growth/margin profile, **deal date (≤18–24 months; rate environment matters)**, **deal type (asset vs stock; control)**, **terms** (cash vs contingent). Exclude **distressed** sales and non-arm's-length deals.

### 11.2 Multiple basis
| Basis | When | Pitfalls |
|---|---|---|
| **SDE multiple** | Owner-operated, <~$1M earnings | Not comparable to EBITDA multiples |
| **EBITDA/EBIT multiple** | Professionally managed; >~$1M | **Adjusted vs reported** EBITDA; TTM vs forward |
| **Revenue multiple** | Software/recurring (ARR), early-stage, services with similar margins | Hides margin and growth differences |
| **Gross profit/ARR multiple** | SaaS | Growth-dependent |
| **Rules of thumb** (e.g., "x% of annual sales") | **Cross-check only** | Industry folklore; ignores profitability |
**Indicative levels (Oct 2026; population-specific):** Main Street **~2.7× SDE** average (**top quartile ~3.5×, bottom ~1.9×**, one practitioner source); **PE-backed middle market ~7.0–7.3× EBITDA** (GF Data); LMM bands **~3–8× EBITDA** with strong size effect (**no reliable single LMM multiple**). **Use them to sanity-check, not to price.**

### 11.3 Adjusting for differences: the regression method
`ln(EV/EBITDA) = b0 + b1·ln(EBITDA) + b2·growth + b3·margin + b4·recurring + b5·top-customer share`.
**Verified on synthetic data** (220 transactions; true function known; observed prices carry 12% deal-specific noise):
| Coefficient | Truth | Recovered |
|---|---|---|
| ln(EBITDA) | 0.20 | **0.20** |
| Growth | 1.2 | 0.99 |
| Margin | 0.8 | 0.73 |
| Recurring share | 0.35 | 0.40 |
| Top-customer share | −0.9 | −0.76 |
R² = 0.82; residual SD 0.116.
**Out-of-sample over 150 random subjects (median / 90th-percentile EV error):**
| Method | Median | 90th pct |
|---|---|---|
| Median multiple of all comps | **16.4%** | 36.9% |
| Size-band median (EBITDA ±50%) | **12.1%** | 27.3% |
| **Regression** | **1.7%** | 4.0% |
**Lesson:** *comparing a $1.5M-EBITDA company to the median of all deals* is the most common amateur error. ⚠️ In real data, expect **larger** errors (omitted variables, thin samples), use **≥50 observations** for a regression, and sanity-check coefficients' signs and magnitudes.

### 11.4 Multiple traps
- **Average of ratios vs ratio of medians** (median price $349,250 ÷ median cash flow $155,921 = **2.24×**, while the reported average multiple is ~2.7×).
- **Headline vs cash multiple:** a "5× EBITDA" deal with 30% earnout and a seller note is **less than 5× in present value** (§18).
- **EV vs equity price:** confirm whether the multiple applies to cash-free, debt-free EV.
- **Stale multiples:** a 2021 multiple is not a 2026 multiple (rates).

---

## §12. Income Approach

### 12.1 DCF steps
1. **Forecast** 5 years of revenue, EBITDA, capex, Δ working capital, taxes (**be realistic: growth fades toward the long-run rate**; a margin that expands forever is a red flag).
2. **FCFF** = EBIT(1−t) + D&A − capex − ΔNWC (`fcff()`).
3. **Discount rate**: CAPM build-up (§12.2) or WACC.
4. **Terminal value:** Gordon `CF₅(1+g)/(r−g)` or exit multiple; **cross-check each against the other** (`dcf()` reports implied exit multiple and implied perpetual growth).
5. **EV** = PV(explicit) + PV(TV). Then bridge to equity (§14.3).

### 12.2 Cost of capital build-up (October 2026 inputs; placeholders flagged)
`Ke = Rf + β×ERP + size premium + company-specific premium`
| Input | Value used | Basis |
|---|---|---|
| **Rf** | **5.6%** | Kroll rule: higher of 3.5% normalized or the **spot 20-year Treasury** (I did not retrieve the 20-yr yield; with the 10-yr ~5.3% and the 30-yr ~5.66%, ~5.5–5.6% is a reasonable placeholder: **verify**) |
| **ERP** | **5.0%** | Kroll recommended US ERP (verify for later updates) |
| **β** | 1.1 | Relevered industry beta (`unlever_beta`/`relever_beta`) |
| **Size premium** | 2.0% | Placeholder; **support with a data source** (Kroll/Duff & Phelps size study) |
| **Company-specific** | 2.0% | Judgment (concentration, key person); **don't double count with cash-flow haircuts** |
| **Kd (pre-tax)** | 10.0% | ~Prime 7.00% + ~3% (SBA-type pricing); use the target's likely borrowing cost |
| **Debt weight** | 30% | Market-participant capital structure |
| **Tax** | 25% | Combined federal/state |
→ **Cost of equity 15.1%; WACC 12.82%.**
**Small-company reality:** discount rates of **12–25%** are common for small private companies; **a "10% WACC" for a $3M-EBITDA business is a red flag.**
**Sanity check — implied discount rate of a deal:** `r = CF₁/Price + g` (`implied_discount_rate()`); a buyer paying 2.7× SDE on a flat business is underwriting **~37% unlevered return** to a *replacement-labor-adjusted* cash flow: that's compensation for owner labor plus risk.

### 12.3 Verified worked example ($3.0M EBITDA, 6% growth for 5 years)
- **FCFF ($M):** 2.05, 2.17, 2.30, 2.44, 2.59.
- **EV at WACC 12.8%, g = 3% = $22.92M = 7.64× current EBITDA;** **terminal value = 65% of EV; implied exit multiple 6.8×** year-5 EBITDA.
| | g = 2% | g = 3% | g = 4% |
|---|---|---|---|
| r = 10.8% | 26.40 | 28.89 | 32.11 |
| **r = 12.8%** | 21.41 | **22.92** | 24.76 |
| r = 14.8% | 17.98 | 18.97 | 20.13 |
- **Rate sensitivity:** if the discount rate were **1.3 points lower** (e.g., a 4.3% instead of 5.6% risk-free rate), **EV = $26.48M, +15.5%**. *This is how higher long yields compress DCF values, even where multiples in small deals look stubborn.*
- **Identity check:** a constant-growth DCF equals the closed form `CF₁/(r−g)` exactly (test passes); `capitalized_earnings(100, 0.11, 0.03) = 1,287.5`.
- **7.6× DCF vs 5–7× market** → investigate: aggressive growth/margins, too-low discount rate, or a high-quality asset worth a premium.

### 12.4 Capitalization of earnings
`Value = normalized cash flow × (1+g) / (r − g)`. Use for **stable** small businesses; the cap rate `r − g` is the reciprocal of a multiple (a **25% cap rate = 4× multiple**).

---

## §13. Asset Approach

- **Adjusted net asset value:** restate assets/liabilities to fair value (real estate, equipment, inventory, intangible assets), subtract liabilities, including contingent ones.
- **Use** for asset-heavy, holding, **loss-making**, or distressed companies; as a **floor** for going-concern value.
- **Liquidation:** *orderly* (time to sell) vs *forced* (auction); forced values can be a fraction of book.
- **Real estate:** value the **property** separately from the **operating business** (a lease at market rent isolates operating earnings).
- **Excess-earnings (formula) method:** historically used in tax and divorce; widely criticized as unreliable; use only if required.
- **Intangibles** (customer relationships, brand, technology): separately identifiable intangibles are valued mostly for **financial reporting** (ASC 805), not price negotiation.

---

## §14. Discounts, Premiums and the Bridge to Equity

### 14.1 Levels of value and discounts (support each one)
- **Minority/lack of control (MD)**, **lack of marketability (DLOM)**, **key-person**, **customer concentration**, **size/specific-company risk**. Typical DLOM discussions run **~20–35%** in practice (restricted-stock studies, pre-IPO studies, option-pricing models); **courts vary** and state-law "fair value" standards often **disallow** them (§30).
- **Apply sequentially** (multiplicative): `apply_discounts(1000, dlom_pct=25, key_person_pct=10)` → **$675 (−32.5% combined)**.
- **Don't double count:** if the discount rate already includes a company-specific risk premium for concentration, **don't** also discount the value for the same concentration.
- **Control premium** implied by a minority discount `MD`: `1/(1−MD) − 1`; 20% → **25%**.

### 14.2 Premiums
Strategic **synergies**, scarcity, auction dynamics and **investment value** can exceed FMV: legitimate for a buyer's offer, **not** for an FMV appraisal.

### 14.3 EV → equity bridge (cash-free, debt-free deals)
`Equity proceeds = EV − debt − debt-like items − NWC shortfall + cash`.
**Debt-like items:** capital leases, **deferred revenue** (if cash already collected and costs to serve remain), **unpaid taxes**, accrued bonuses/PTO, **customer deposits**, deferred capex, litigation reserves, earnout obligations, shareholder loans. **Example:** EV $5.0M, debt $600k, debt-like $150k, NWC shortfall $100k, cash $250k → **equity $4.4M**.
**Working-capital peg:** set at the **normalized (average) level** over the prior 12 months, adjusted for seasonality; **a peg set too low transfers value to the seller; too high, to the buyer.**

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
