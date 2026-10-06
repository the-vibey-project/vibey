---
id: skill-12-income-approach-3a5fbb17f7
purpose: 12 income approach
source: src/vibey_tools/skills/plugins/business-valuation/skills/bizval-valuing-a-private-company/SKILL.md
requires: ["skill-11-market-approach-ee2503b983"]
links: ["skill-13-asset-approach-a1ab6ad862"]
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
