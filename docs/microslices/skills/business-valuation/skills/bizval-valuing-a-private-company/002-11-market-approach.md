---
id: skill-11-market-approach-ee2503b983
purpose: 11 market approach
source: src/vibey_tools/skills/plugins/business-valuation/skills/bizval-valuing-a-private-company/SKILL.md
requires: ["skill-10-normalizing-earnings-8a3a60c967"]
links: ["skill-12-income-approach-3a5fbb17f7"]
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
