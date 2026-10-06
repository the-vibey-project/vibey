---
id: skill-15-worked-example-sandbox-verified-and-the-recipe-for-any-house-e63c6e4331
purpose: 15 worked example sandbox verified and the recipe for any house
source: src/vibey_tools/skills/plugins/home-valuation/skills/homeval-comps-adjustments-and-avms/SKILL.md
requires: ["skill-14-avms-zestimate-redfin-estimate-and-friends-e9012a6ff4"]
links: []
---

## §15. Worked Example (sandbox-verified) and the Recipe for Any House

### 15.1 Setup (synthetic market with known truth)
220 synthetic closed sales (price function with known elasticities and a +0.15%/month market drift), noise 4.5% log-sd. Subject: 2,000 sf, 4 bd, 2.5 ba, 9,500 sf lot, built 2004, condition 4/5, 2-car garage, two-story. **Ground-truth value today: $261,623.** (The tools do not see this.)

### 15.2 Steps and results (run `python3 scripts/test_homeval.py`)
1. **Market stats (last 90 days):** n = 49, median price $220,500, median $/sf $126, median DOM 49, 24.5% over list, 26.5% with price cut.
2. **Time drift (regression on date):** +0.227%/month (truth +0.15%; noisy by construction, so capped to ±0.5%).
3. **Rank comps** → 71 within guardrails (≤1 mile, ≤6 months, GLA within 20%); use top 6.
4. **Adjustment grid** (comp → subject):

| Comp | Sale | Time | GLA | Baths | Garage | Cond. | Net adj. | Adjusted | Net % | Gross % |
|---|---|---|---|---|---|---|---|---|---|---|
| 116 | 269,000 | +1,022 | −268 | 0 | 0 | −8,101 | −7,347 | **261,653** | −3 | 3 |
| 62 | 250,400 | +391 | +1,371 | +7,500 | 0 | 0 | +9,262 | **259,662** | +4 | 4 |
| 186 | 256,700 | +1,493 | +933 | 0 | −8,000 | −7,746 | −13,320 | 243,380 | −5 | 7 |
| 8 | 227,000 | +2,392 | +5,183 | 0 | +8,000 | 0 | +15,575 | 242,575 | +7 | 7 |
| 110 | 234,800 | +3,004 | −4,259 | +7,500 | +16,000 | 0 | +22,245 | 257,045 | +9 | 13 |
| 28 | 263,100 | +1,412 | −4,339 | 0 | 0 | +7,935 | +5,009 | **268,109** | +2 | 5 |

5. **Reconcile** (weight by 1/(1+gross%/10) and similarity; use the 3 lowest-gross comps: 116, 62, 28): **$262,615 → +0.38% vs truth.** Range of best: $259,662–$268,109 (spread ~3%). *Unweighted median of all six: $258,354.*
6. **Hedonic regression** (n = 220, R² = 0.948, log-residual sd 0.045): sqft elasticity **0.838** (truth 0.85); **point $257,605**, p10–p90 **$243,293–$272,759**, implied MdAPE ~3.0%; **−1.54% vs truth**. (Drift coefficient 0.06%/mo vs truth 0.15% shows why §12 says use multiple methods.)
7. **Triangulate** (60% comps / 40% regression): **$260,611 (−0.39% vs truth).**
8. **Band for an off-market AVM at 7.2% median error:** $241,847–$279,375, *wider than the 3% spread of the best comps*, the point of doing real comps.

### 15.3 What the example teaches
- Comps with **gross adjustments ≤5%** (116, 62, 28) are the evidence; comp 110 (13% gross, three adjustments) is supporting, not core.
- **Condition and garage drive the largest errors**; document them with photos.
- The regression was **less accurate than good comps** (−1.5% vs +0.4%) but **stable**, and it flagged the right *range*.
- The AVM-style band was **~4× wider** than the comp spread: a quantification of why careful work beats a single automated number *when the subject is comparable and the data is good.*

### 15.4 Recipe: valuing any real house (do these in order)
```
INPUTS : address, GLA, beds/baths, lot, year, condition notes, upgrades+dates, permits
1  Pull closed sales: same property type, last 6 mo (12 if thin), 1 mile (widen stepwise), GLA ±20%.
2  Verify each comp with two sources; log concessions/financing; photograph-based condition score (1–5, consistent).
3  Rank with score_comps(); keep guardrail-passing, top 5–6 plus 2–3 active/pending as supporting.
4  Estimate time drift 2 ways (repeat sales/regression/index) and from live pending/active evidence; cap at ±0.5%/mo.
5  Build the grid with adjust_comps(); replace placeholder amounts with LOCAL paired-sale/regression numbers.
6  Drop OVER-ADJUSTED comps; reconcile() with top 3 lowest-gross; record spread.
7  If ≥50 local sales: hedonic_fit()/hedonic_predict(); hold-out MdAPE; compare with step 6.
8  Collect 3–5 AVMs; use their spread as an uncertainty indicator, not as the answer.
9  Check live competition: best 3 active homes that beat the subject on price/feature; adjust expectation downward if they undercut.
10 State value as a RANGE + confidence + assumptions + what would change it.
```
**Confidence statement template:** *"Opinion of value (informal, not an appraisal): $X–$Y, most likely about $Z, effective [date]. Based on N closed comps (list), adjusted to cash-equivalent, time-adjusted at [rate] and cross-checked with a regression (MdAPE [x]%) and AVMs ($a–$b). Largest uncertainty: [condition/layout/time]. A change of ±[k]% in [assumption] moves value by ±$m."*

### 15.5 Tool calls (copy-paste)
```python
import pandas as pd, homeval as hv
TODAY = pd.Timestamp("YYYY-MM-DD")
subj = hv.Subject(sqft=..., beds=..., baths=..., lot_sqft=..., year_built=..., condition=..., garage=..., style="...", lat=..., lon=...)
ranked = hv.score_comps(subj, comps_df, TODAY)               # columns in docstring
good = ranked[ranked.within_guardrails].head(6)
drift = hv.time_adjustment_pct_per_month(comps_df)            # cap to ±0.5
adj = hv.adjust_comps(subj, good, TODAY, monthly_drift_pct=max(min(drift,0.5),-0.5),
                      bath_adj=LOCAL, garage_bay_adj=LOCAL, lot_per_sqft=LOCAL)
rec = hv.reconcile(adj, scores=good.score)
m = hv.hedonic_fit(comps_df, TODAY); pred = hv.hedonic_predict(m, subj)
tri = 0.6*rec["estimate"] + 0.4*pred["point"]
```
