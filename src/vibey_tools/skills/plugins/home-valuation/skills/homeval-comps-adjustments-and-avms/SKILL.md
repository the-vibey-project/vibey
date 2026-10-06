---
name: homeval-comps-adjustments-and-avms
description: "Use when valuing one specific house: how to select comparable sales (the priority-ordered rules), build the adjustment grid in the correct direction and order, derive adjustments from the market (paired sales, regression) instead of construction cost, estimate market-conditions/time adjustments, run a hedonic regression cross-check, interpret Zestimate/Redfin/AVM error honestly (1.78% on-market vs 7.20% off-market median error, Aug 2026), reconcile to a value range, and a sandbox-verified worked example with the scripts/homeval.py toolkit."
---

# Home Valuation and Market Research: Comps, Adjustments, Regression and AVMs

> **Part 3 of 7** of the *Home Valuation and Market Research* reference (plugin `home-valuation`), covering §10–§15. Sibling skills: `homeval-concepts-methods-and-market-structure` (§0–§4), `homeval-market-analysis-and-timing` (§5–§9), `homeval-buyer-playbook` (§16–§20), `homeval-seller-playbook` (§21–§25), `homeval-diligence-risk-and-investment` (§26–§30), `homeval-reference` (§31–§35). Code: `scripts/homeval.py`, `scripts/test_homeval.py`.
>
> **Currency:** The method is stable (it is the core of the Appraisal Institute / USPAP approach). The AVM error figures are Zillow's published numbers as of **Aug 8, 2026** and will refresh.

> **⚠️ Scope.** This is how to do a *careful informal valuation*. It is **not a USPAP-compliant appraisal** and is not a substitute for one where a lender, court or tax authority requires one. The worked example in §15 uses a **synthetic market with a known true price function**, so the tools' accuracy can be verified; real markets are noisier and have unobserved condition and quality.

> **The three ideas:**
> 1. **⚠️ The best comp is the one that needed the least adjustment**, not the one that sold highest or lowest. Every adjustment is an opinion that injects error; **minimise the number and size of them** (§10–§11).
> 2. **⚠️ Adjustments come from the market, not from the contractor.** A $40,000 kitchen does not add $40,000. Derive adjustments from paired sales or regression (§11, §13).
> 3. **⚠️ Report a range, not a number.** If your comps-based value, regression and best AVMs agree within ~3–4%, say so with moderate confidence. If they spread 10%+, the honest answer is "it depends on condition/terms; here is how to resolve it" (§15.4).

---

## §10. Selecting Comparable Sales

### 10.1 The priority-ordered rules
Rank candidates; do not just filter. **Hard guardrails** (relax only with a written reason) then **ranked similarity**.

| Criterion | Standard starting guardrail | Widen when… | ⚠️ Pitfall |
|---|---|---|---|
| **Status** | **Closed** arm's-length sales | Support only with active/pending (§10.3) | **List prices are not comps.** They are asks |
| **Recency** | ≤ 90 days ideal; ≤ 6 months acceptable | Thin market: ≤ 12 mo with time adjustment | Stale comps in a moving market are the most common error (§12) |
| **Distance** | ≤ 1 mile (urban/suburban) | Rural: 3–10+ miles | Don't cross school-zone, flood-zone, busy-road, HOA or municipal-tax lines without adjusting |
| **Size (GLA)** | ± 10–20% | Large/unique homes | GLA measured differently (use ANSI Z765 logic); below-grade ≠ GLA |
| **Style / design** | Same (ranch with ranch) | Few comps | Cross-style comps need larger adjustments |
| **Age / quality** | ± 10–15 years and same quality tier | Thin market | A renovated 1970s house is closer to newer than to its unrenovated twin |
| **Condition** | Same band (5-point scale you apply consistently) | Always adjust if different | **Flips as comps for unrenovated homes** = overvaluation |
| **Beds/baths/garage/lot** | ± 1 bed / ± 1 bath / same garage count | – | Count above-grade only |
| **Property rights / type** | Same (fee simple SFR vs SFR) | Never mix | Condo vs SFR, leasehold vs fee, new vs resale: different markets |
| **Transaction type** | Exclude REO/short sales/relatives/estate quick-sales *unless the market is distressed* | Distress-heavy local market | Non-market sales understate value |

### 10.2 Ranking score
`homeval.score_comps()` computes a transparent similarity score: normalised gaps in distance, recency, GLA, age, beds, baths, condition, lot and style, with heavier weight on GLA, condition and location. **Keep the score components visible** so you can explain *why* a comp ranked where it did; an unexplainable rank is a black box you will not defend in negotiation.

### 10.3 How many, and the supporting cast
- **Minimum:** 3 closed comps; **good practice:** 5–6, plus **supporting evidence**: (a) *active listings* (the competition and the ceiling), (b) *pending* listings (current demand, price per `pending` date), (c) *expired/withdrawn* listings in the last 6 months (prices the market rejected). **A price above the cheapest comparable active listing that is better is a price that will not sell.**
- **Bracket the subject:** ideally comps both above and below on key features (size, condition, price). A set all *smaller* than the subject forces extrapolation.
- **Use the same tie-breaker an appraiser does:** *which would a buyer of this house pick instead?* That is the substitution principle.

### 10.4 Data hygiene
Verify each comp with at least two sources (MLS or portal + county recorder). Check: sale date vs recording date, **concessions** (sellers paid X), **financing** (seller financing, assumption, buydown), **GLA vs permitted** (unpermitted additions), **lot** (usable vs gross), **condition** from photos (kitchen/baths/flooring/roof), **days on market**, price history (cuts, relists).

---

## §11. The Adjustment Grid

### 11.1 Direction (get this right or every number is backwards)
**Adjust the comp toward the subject.**
- Comp is **superior** to the subject on a feature → **subtract** (negative adjustment).
- Comp is **inferior** → **add** (positive adjustment).
- Example: comp has a third garage bay the subject lacks → subtract the value of a bay. Comp is 150 sf smaller → add 150 × marginal $/sf.

### 11.2 Order (USPAP/URAR sequence)
1. **Transactional adjustments first** (applied in order, each on the cumulative price): **property rights**, **financing terms**, **conditions of sale**, **expenditures immediately after purchase** (deferred maintenance).
2. **Market conditions (time)**, applied to the *adjusted* price (§12).
3. **Then property characteristics**: location, site, view, design/quality, age/condition, GLA, rooms, garage, extras.

### 11.3 Where the numbers come from (in descending reliability)
| Method | How | When to use |
|---|---|---|
| **Paired sales** | Two sales identical except one feature; the price gap ≈ the feature's value | Rich markets; best evidence |
| **Regression (hedonic)** | Coefficients on log price (§13) | ≥ ~50 local sales; controls many features at once |
| **Matched-pair inference from listings** | Compare listings pre/post renovation, or same model homes with/without a feature | Cross-check |
| **Cost-to-cure** | Cost of fixing a defect (not of building the feature new) | Deferred maintenance, defects |
| **Depreciated cost** | Replacement cost new − depreciation | Only when market evidence is absent; it overstates |
| **Survey/rule-of-thumb** (Cost vs Value etc.) | Industry averages | Last resort; ⚠️ these are *survey-based opinions* (§23) |

### 11.4 Typical magnitudes (starting hypotheses ONLY; replace with local evidence)
| Feature | Typical treatment | ⚠️ Caveat |
|---|---|---|
| **GLA** | **~30–50% of the comp's average $/sf** for each marginal sf (marginal sf < average sf) | Using the average $/sf over-adjusts; smaller differences → smaller error |
| **Bathroom** | A bath of a type (full vs half) is worth ~low-to-mid five figures in typical markets; use local pairs | Count above-grade full/half consistently |
| **Bedroom** | Often near zero *after* adjusting GLA; bed count matters at thresholds (3 vs 4) | Adjusting both GLA and beds double-counts |
| **Garage bay** | Low-to-mid four to low five figures | Attached vs detached, door height, workshop |
| **Condition** | ~2–5% of price per condition step on a consistent scale | Largest and most subjective adjustment; document with photos |
| **Lot** | $/sf for *excess usable* land, not gross | Slope, flood, easements, shape |
| **Pool** | Often **near zero or negative** in many climates | Region-dependent; verify locally |
| **Age/updating** | Small per-year effect, large step effects from systems (roof, HVAC) | Overlaps with condition; avoid double counting |
| **Location** | Paired sales across the boundary (school, road, flood) | Often the largest single factor |

`homeval.adjust_comps()` defaults are **placeholders** (e.g., $7,500/bath, $8,000/garage bay, condition at 3% per step, GLA at 40% of $/sf). Override each with local evidence.

### 11.5 Size limits (quality control)
Traditional underwriting guidance flags **net adjustments > ~15%** and **gross adjustments > ~25%** of a comp's price (⚠️ guidelines, not law). `adjust_comps()` marks `OVER-ADJUSTED` above these; drop such comps unless nothing else exists, and say so.

### 11.6 Cash-equivalent adjustments (financing and concessions)
If a seller paid concessions that were reflected in the price, the cash-equivalent price is lower. Simple approach: **subtract seller-paid concessions** (and the value of any below-market seller financing/buydown) from the sale price before other adjustments. Document it; many "paid-over-list" sales evaporate after this step.

---

## §12. Market-Conditions (Time) Adjustment

**Problem:** a comp that sold 5 months ago reflects the market 5 months ago. In a market moving +/−0.5% per month that is ±2.5%; during a rate shock (§7) it can be larger.

**Methods (use at least two):**
1. **Paired resales:** the *same house* selling twice (repeat sales) is the cleanest signal.
2. **Regression on sale date** (log price per sf on months, `time_adjustment_pct_per_month()`): noisy with fewer than ~30 sales.
3. **Index:** metro Case-Shiller / FHFA HPI / Zillow ZHVI / Cotality HPI monthly changes.
4. **Live evidence:** pending list-to-contract prices and active listing price cuts show where the market is *now*; if pending sales are below recent closings, drift is negative even if the index is lagging.
5. **Sanity cap:** ±0.5%/month is a plausible range outside crises; extrapolating 2–3%/month from a seasonal bump is a classic error.

⚠️ **Do not apply an annual appreciation rate mechanically in a market with a rate shock.** Re-estimate after any move of ~0.5+ points in rates.

---

## §13. Hedonic (Regression) Cross-Check

**Model:** `ln(price) = β0 + β1·ln(sqft) + β2·beds + β3·baths + β4·ln(lot) + β5·age + β6·condition + β7·garage + β8·months_since_sale + ε`.

**Why log price:** effects become percentages; heteroscedasticity falls; coefficient on `ln(sqft)` is an elasticity (in the example: 0.84 vs a true 0.85: a **1% bigger house costs ~0.84% more**, not 1%).

**When to run it:** ≥ ~50–100 sales in your market area in the last 6–12 months, same property type. Add **neighborhood/school-zone dummies** if you can.

**Checks (do all):**
- **Hold-out test:** fit on 80%, predict 20%; report median absolute % error (MdAPE).
- **Residual plot:** look for clusters (a street or condition class the model misses), heavy tails, trend with price.
- **Robust standard errors** (the toolkit uses HC0); sign and size sanity on every coefficient (age negative? condition positive?).
- **Outliers:** examine, don't auto-drop (they may be flips or distress).
- **What it cannot see:** condition beyond your scale, finishes, view, layout, deferred maintenance, lot quality. **Condition is the dominant omitted variable in real data**, so treat a regression as a *cross-check on comps*, never the sole answer.

**Interpretation:** `price_band` and `hedonic_predict()` return p10–p90 using the model's residual spread. `approx_mdape_pct = 0.6745 × residual sd × 100` ≈ the typical absolute % error.

---

## §14. AVMs: Zestimate, Redfin Estimate and Friends

### 14.1 Published accuracy (the honest numbers)
- **Zillow (own published, accuracy data refreshed Aug 8, 2026): median error 1.78% for on-market homes and 7.20% for off-market homes.** (Other Zillow-cited snapshots in 2026 ranged 1.9–2.4% on-market and 6.9–7.5% off-market. ⚠️ Trade press repeats different vintages; use the live Zillow page.)
- **Redfin Estimate:** reported at ~**1.98%** on-market and ~**7.66%** off-market (older published figure).
- **By geography:** off-market median error varies widely by state (e.g., ~5.3% in Colorado vs ~12.7% in Vermont in Zillow's Apr 2026 table; ⚠️ third-party summary); **rural/thin markets: 8–12%+** is reported.
- **Why on-market is 4× better:** the estimate incorporates the **list price, description and photos**, i.e., it partly copies the human CMA. An off-market Zestimate is the real model.

### 14.2 What "median error" means
Half of estimates are **worse** than the median; the tail is much worse. On a $430,000 home, 7.2% = **±$31,000** for the *median* case. Zillow publishes the share within 5%, 10% and 20% of the sale price: **check the within-10%/within-20% shares for your metro** to see tail risk. Do not interpret "±median error" as a confidence interval for your house; it's roughly a 50% interval (§15.4).

### 14.3 How to use AVMs well
1. **Collect 3–5** (Zillow, Redfin, Realtor.com, Cotality/CoreLogic, a county value, HouseCanary or bank tool). **Their spread is an uncertainty signal**: wide spread → model doesn't know your house.
2. **Correct the inputs:** beds, baths, GLA, lot, upgrades, year, condition. Claim your home on Zillow and edit facts; Redfin lets you update details.
3. **AVMs lag turning points** and cannot see: kitchen quality, layout flaws, view, road noise, deferred maintenance, additions. Treat AVMs as the *first screen*, not the answer.
4. **Never use an AVM alone to price, offer or refinance.** Use it to decide whether to invest a weekend in a real analysis.
5. **LLMs are not valuation tools.** A language model with no comps data will *fabricate* a plausible number. Use an LLM for structure (checklists, drafting, code) but feed the numbers from real sales data. Same standard for any "AI CMA" product: ask what comps and what error rate.

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
