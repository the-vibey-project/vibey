---
id: skill-15-worked-example-sandbox-verified-and-the-recipe-071ecc3c4e
purpose: 15 worked example sandbox verified and the recipe
source: src/vibey_tools/skills/plugins/car-valuation/skills/carval-valuing-a-specific-vehicle/SKILL.md
requires: ["skill-14-guides-special-vehicle-types-and-collectors-f4d4228a4b"]
links: []
---

## §15. Worked Example (sandbox-verified) and the Recipe

### 15.1 Setup (synthetic market with known truth)
260 synthetic listings/sales of one model (3 trims, 2019–2024). True price depends on age (retention curve), mileage (~2.2% per 10k miles vs expected), condition (3%/step), accidents (7% each), owners (1% each), drift (−0.4%/month), and CPO (+$1,500); active listings are priced ~3% above transaction. **Subject:** 2022 EX, 38,000 miles, condition 4/5, one owner, clean history. **Ground-truth transaction value: $21,209.**

### 15.2 Steps and results (`python3 scripts/test_carval.py`)
1. **Comps:** 19 within guardrails (7 sold, 12 active); use top 6.
2. **Mileage adjustment:** estimated **$0.049/mile** from the comps (truth ≈ $0.05).
3. **Adjustment grid** (comp → subject; "Other" = owners and CPO):

| Comp | Price | Ask→sale | Time | Miles | Year | Cond. | Accident | Other | Net | Adjusted | Gross % |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 108 | 21,670 | 0 | −139 | +363 | 0 | 0 | 0 | +430 | +654 | **22,324** | 4 |
| 247 | 19,520 | −586 | −52 | +554 | 0 | 0 | +1,322 | +189 | +1,427 | 20,947 | 14 |
| 119 | 21,380 | 0 | −143 | +392 | 0 | 0 | 0 | −1,287 | −1,038 | **20,342** | 11 |
| 219 | 21,860 | −656 | −106 | −525 | 0 | +633 | 0 | 0 | −653 | **21,207** | 9 |
| 157 | 19,660 | −590 | −98 | +186 | 0 | +569 | +1,328 | 0 | +1,396 | 21,056 | 14 |
| 113 | 23,780 | −713 | −157 | −466 | −1,604 | 0 | 0 | +229 | −2,711 | 21,069 | 13 |

4. **Reconcile** (weight by 1/(1+gross%/5); top 4 by lowest gross): **$21,397** (+0.88% vs truth); best-comps range $20,342–$22,324 (spread ~9%).
5. **Hedonic regression** (n = 260, R² = 0.954, log-residual sd 0.043): point **$21,386** (+0.83%), p10–p90 **$20,231–$22,606**, implied MdAPE ~2.9%; drift coefficient −0.45%/month (truth −0.40%).
6. **Triangulate** (60% comps / 40% regression): **$21,392 (+0.86%)**.
7. **Naive contrast:** the mean of all same-trim 2021–2023 prices was **$20,687 (−2.5%)**: close *by luck*, which is why the next test matters.

### 15.3 Accuracy over 120 random subjects (synthetic truth)
| Method | Median abs. error | 90th percentile |
|---|---|---|
| Naive mean of same trim, year ±1 | **4.4%** | **12.0%** |
| Adjusted comps | **1.1%** | **3.1%** |
| Hedonic regression | **1.1%** | **2.0%** |
| Triangulated (60/40) | **0.7%** | **2.1%** |
⚠️ **These are best-case numbers:** the simulated noise is small (3% on transactions), the regression matches the data-generating process, and condition is observed perfectly. **Expect 2–3× larger errors in real data**, and the ranking (naive worst; triangulated best) to hold.

### 15.4 Recipe: valuing any car (do these in order)
```
INPUTS : VIN, year/trim/engine/drivetrain, miles, condition grade (1–5 rubric), history/title, options, location
1  Decode the VIN (build sheet) and verify trim/options; check NHTSA recalls.
2  Pull 6–10 comps (≥3 sold) within guardrails; log VIN/URL, date, price, miles, trim, condition, history, status.
3  Convert asking to expected sale (3% placeholder; calibrate).
4  Estimate $/mile from comps (≥15 comps), drift from MUVVI/MMR/regression, and condition step from pairs.
5  Build the grid with adjust_listings(); drop OVER-ADJUSTED comps; reconcile().
6  If ≥50 comps: hedonic_fit()/hedonic_predict(); compare.
7  Pull 2–3 guides (KBB, Edmunds, J.D. Power) + 1–2 real offers (instant offers or dealer quotes); compare.
8  Pre-purchase inspection and history report adjust the number (§26); document findings.
9  State a RANGE, most-likely value, walk-away (buy) or floor (sell), and what would change it.
```
**Confidence statement template:** *"Informal opinion of value (not an appraisal): $X–$Y, most likely about $Z, effective [date], for a [year trim] with [miles], condition [n]/5, [title/history]. Based on N comps (K sold), adjusted for mileage ($/mile), condition, history and asking-to-sale; cross-checked by a regression (MdAPE [x]%) and guides ($a–$b). Largest uncertainty: [condition/history/market drift]. A ±1 condition step moves value by ±$m."*

### 15.5 Tool calls
```python
import pandas as pd, carval as cv
TODAY = pd.Timestamp("YYYY-MM-DD")
subj = cv.Vehicle(year=..., miles=..., trim="...", condition=..., owners=..., accidents=..., cpo=False)
ranked = cv.score_listings(subj, comps_df, TODAY)            # columns in docstring
good = ranked[ranked.within_guardrails].head(6)
per_mile = abs(cv.mileage_adjustment_per_mile(comps_df))     # ≥15 comps, same trim/gen
adj = cv.adjust_listings(subj, good, TODAY, per_mile=per_mile, ask_to_sale_discount_pct=3.0,
                         condition_step_pct=3.0, accident_pct=7.0, monthly_drift_pct=-0.4)
rec = cv.reconcile(adj)
m = cv.hedonic_fit(comps_df, TODAY); pred = cv.hedonic_predict(m, subj, TODAY)
tri = 0.6*rec["estimate"] + 0.4*pred["point"]
```
