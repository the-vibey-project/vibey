---
id: skill-28-the-income-approach-and-investment-math-46f0b9bfaf
purpose: 28 the income approach and investment math
source: src/vibey_tools/skills/plugins/home-valuation/skills/homeval-diligence-risk-and-investment/SKILL.md
requires: ["skill-27-climate-insurance-and-location-risk-as-valuation-inputs-2ea8f8eeeb"]
links: ["skill-29-specialty-valuation-situations-aba40ce7cd"]
---

## §28. The Income Approach and Investment Math

### 28.1 Definitions (use consistently)
| Metric | Formula | Notes |
|---|---|---|
| **GSR** gross scheduled rent | Σ market rents for 12 months | Use *market* rent from rent comps, not the seller's pro forma |
| **EGI** effective gross income | GSR × (1 − vacancy) + other income | Vacancy 5–10% typical; use local data |
| **NOI** net operating income | EGI − operating expenses | **Excludes** debt service, depreciation, income tax and capital reserves. State your reserve separately |
| **Operating expenses** | Taxes (re-assessed), insurance, maintenance, management (8–10% typical), utilities, HOA, turnover, professional fees | **Expense ratio ~35–50% of EGI** is a common planning range for single-family/small multifamily (⚠️ rule of thumb; underwrite line by line) |
| **Cap rate** | NOI ÷ price | Unlevered yield; compare to *current* alternatives |
| **Value by income** | NOI ÷ market cap rate | Cap rate must come from **comparable sales of income property** |
| **GRM** | Price ÷ gross annual rent | Fast screen; ignores expenses and quality |
| **DSCR** | NOI ÷ annual debt service | Lenders commonly want ≥1.20–1.25 for investor loans (verify) |
| **Cash-on-cash** | (NOI − debt service) ÷ cash invested | Include closing costs and rehab in cash invested |
| **IRR / equity multiple** | Discounted cash-flow of NOI + sale | Needs rent growth, expense growth, exit cap and costs |
| **Break-even occupancy** | (Opex + debt service) ÷ GSR | Resilience metric |

### 28.2 Verified example at 7.28% (toolkit)
$360,000 purchase, rent $2,400/mo ($28,800/yr), 6% vacancy, $9,800 opex, 75% LTV ($270,000), 7.28% 30-yr: **NOI $17,272 → cap rate 4.80%; GRM 12.5; debt service $22,168 → DSCR 0.78; cash-on-cash −4.86%.** **Value at a 6.5% cap = $265,723** (i.e., the market would pay far less than $360k for this income if cap rates are 6.5%).
| NOI-to-value at cap rate | Value |
|---|---|
| 5.0% | $345,440 |
| 6.0% | $287,867 |
| 7.0% | $246,743 |
| 8.0% | $215,900 |
**Rent needed for DSCR ≥ 1.25** with the same costs: **~$3,300/mo (rent/price ≈ 0.92%)**; DSCR 1.0 needs ~$2,850/mo. **So the "1% rule" (rent ≥ 1% of price) is roughly the right order of magnitude to cash-flow with 25% down at ~7.3%; the 0.67% property fails.** ⚠️ The rule ignores taxes, insurance, vacancy and your actual loan; use it only as a screen.

### 28.3 Negative leverage
When the **cap rate < mortgage rate** (here 4.8% vs 7.28%), borrowing *reduces* cash yield; returns then depend on **appreciation and rent growth**, which aren't guaranteed. **Check this before leaning on leverage.**

### 28.4 Rent comps
Use **closed leases and active/expired rental listings**, same type/size/condition/location; verify rent growth with multiple sources; HUD Fair Market Rent as a floor reference (not a market rent); consider tenant quality, concessions, and local regulation (rent control, license, short-term-rental limits). **Short-term rentals** carry **regulatory, seasonality and platform risk**; underwrite conservatively, and confirm legality and HOA permission *before* purchase.

### 28.5 Flip and BRRRR screens
- **70% rule (screen only):** max offer = ARV × 70% − rehab → `seventy_percent_rule_max_offer(330_000, 55_000) = $176,000`. It ignores holding costs, financing, selling costs and local margins; use your own all-in formula.
- **BRRRR (buy-rehab-rent-refinance-repeat):** `brrrr(purchase=210_000, rehab=55_000, arv=330_000, refi_ltv_pct=75, monthly_rent=2_300, opex_pct_of_rent=40, rate_pct=7.28, holding_costs=8_000)` → **all-in $273,000 = 82.7% of ARV; refi loan $247,500; cash left in deal $25,500; NOI $16,560; debt service $20,321; DSCR 0.81; cash flow −$3,761/yr.** ⚠️ At current rates BRRRR often *fails the refinance test* even when it "forces appreciation". Stress-test the refinance at today's rate and appraisal.
- **ARV** must come from **renovated, comparable sales** (§15) in the right school zone: an inflated ARV is the most common flip failure.

### 28.6 Policy/market notes for investors (Oct 2026)
**21st Century ROAD to Housing Act (enacted Jul 11, 2026)** prohibits **large institutional investors** (≥350 single-family homes) from buying additional single-family homes, effective **Jan 7, 2027** for **15 years**, with exceptions (e.g., newly built, renovated-for-sale, certain sales between covered investors). Small investors are outside the definition. ⚠️ Practical effects on pricing are uncertain and contested. For multifamily/commercial intelligence, institutional data (Yardi Matrix) exists; see §33.

---
