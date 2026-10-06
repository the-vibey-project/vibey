---
name: carval-valuing-a-specific-vehicle
description: "Use when valuing one specific car: how to select comparables (sold vs asking, year/trim/mileage/condition/title guardrails), build the adjustment grid (mileage per mile, year, trim, condition, accident history, owners, CPO, asking-to-sale discount, time drift), run a regression cross-check, triangulate with KBB/Edmunds/J.D. Power/MMR without trusting one number, handle EVs (battery state of health), hybrids, trucks, luxury, high-mileage, rebuilt-title and classic/collector cars (Hagerty condition grades), and a sandbox-verified worked example with scripts/carval.py (adjusted comps 1.1% median error vs 4.4% for a naive average)."
---

# Car Valuation and Market Research: Valuing a Specific Vehicle

> **Part 3 of 7** of the *Car Valuation and Market Research* reference (plugin `car-valuation`), covering §10–§15. Sibling skills: `carval-concepts-methods-and-market-structure` (§0–§4), `carval-market-analysis-and-timing` (§5–§9), `carval-buyer-playbook` (§16–§20), `carval-seller-playbook` (§21–§25), `carval-diligence-risk-and-ownership-economics` (§26–§30), `carval-reference` (§31–§35). Code: `scripts/carval.py`, `scripts/test_carval.py`.
>
> **Currency:** The method is stable. Magnitudes (per-mile, condition, accident percentages) are **placeholders to be replaced with local evidence**.

> **⚠️ Scope.** An informal valuation for decision support; **not an appraisal** for insurance, court, tax or lending. The worked example (§15) uses a **synthetic market with a known true price function** so accuracy can be verified; real markets are noisier, and unobserved condition and history are the dominant sources of error.

> **The three ideas:**
> 1. **⚠️ Value the car you are looking at, not the model.** Two identical-looking cars can differ by 15–30% on mileage, condition, history and title. A car's *model average* is a starting point, not an answer.
> 2. **⚠️ Separate asking from selling.** Active listings are asks. Convert them to expected transaction prices (placeholder 3% off), prefer sold data, and read price history and days-on-lot (§10.2).
> 3. **⚠️ Inspection and history turn an estimate into a value.** The number you quote before a pre-purchase inspection (PPI) and a history report is conditional; say so, and adjust after (§26).

---

## §10. Selecting Comparable Cars

### 10.1 Priority-ordered guardrails (relax only with a written reason)
| Criterion | Starting guardrail | Widen when… | ⚠️ Pitfall |
|---|---|---|---|
| **Status** | **Sold** transactions first; active listings as supporting evidence | Few sold comps | An ask is not a price; apply the asking-to-sale discount (§12) |
| **Generation/model year** | Same generation; **± 1 model year** | Rare models | Mid-cycle refreshes and engine/transmission changes |
| **Trim & drivetrain** | **Same trim**, same drivetrain (FWD/AWD/4x4), same engine | Never mix hybrid/ICE/EV | Packages vary within a trim: verify by VIN build data |
| **Mileage** | ± **20,000–25,000** miles | Highly differentiated mileage | Adjust per mile; beware thresholds at 60k/100k/150k |
| **Condition** | Same band; **photos matter** | Always adjust if different | Dealer "excellent" ≠ your grade; use one rubric |
| **History/title** | Same brand status (clean/clean); accident count similar | Specific discounts for brands | **Branded titles belong to a different market** (§14.5) |
| **Seller type** | Match (dealer retail vs private party vs CPO) | – | CPO carries a premium for warranty/inspection |
| **Region/time** | 100–250 miles; ≤ 60–90 days | Rare cars: national, ≤ 180 days | Cross-state tax/fee differences; seasonal 4WD premiums |
| **Options** | Search-relevant options (driver assist, tow package, panoramic roof) | – | Many options add little; a few matter a lot |

### 10.2 Reading a listing's price history and days on lot
- **Newly listed + priced at/above comps:** an *ask*; expect negotiation room.
- **60+ days on lot with 1–2 cuts:** closer to what will actually transact; the **latest** price is more informative than the first.
- **Same car re-listed with a new stock number or by another dealer:** days-on-lot resets; check price history tools and VIN-level history.
- **Price just under a round number or "internet price" requiring financing/add-ons:** the **real price may be higher**; get an itemized out-the-door quote (§18).
- **Private-party ads** are often priced above likely sale (negotiation room 3–8%; ⚠️ rule of thumb) but may be *below* retail for the same car.

### 10.3 Number of comps
Aim for **6–10** with at least **3 sold**; fewer than 5 means a wider confidence band. **Bracket the subject** on mileage and condition (some above, some below), so adjustments are interpolation, not extrapolation.

### 10.4 Sources for comps
Local listing aggregators (CarGurus, Autotrader, Cars.com, TrueCar, CarEdge), dealer websites, Facebook Marketplace/Craigslist (private), enthusiast auction sites with sold results (e.g., Bring a Trailer, Cars & Bids for enthusiast cars), your own offers from CarMax/Carvana, and dealer-sold data when a friendly dealer will share. **Capture each comp's VIN or listing URL, date, price, mileage, trim, condition notes, history and status in a table** (the toolkit expects these columns).

---

## §11. The Adjustment Grid

### 11.1 Direction
**Adjust the comp toward the subject.** Comp is **superior** (lower mileage, better condition, newer) → **subtract**. Comp is **inferior** → **add**.

### 11.2 Adjustment items and where the numbers come from
| Item | Treatment | Source of number (best → worst) |
|---|---|---|
| **Asking → expected sale** | Active listings: −X% (placeholder 3%) | Your market's sold/asking ratio; price-cut history; dealer feedback |
| **Time/market drift** | Compound monthly drift to today | MUVVI/MMR trend; regression on date (§12) |
| **Mileage** | (comp miles − subject miles) × **$/mile** | **Estimate from the comps** (`mileage_adjustment_per_mile()`); guides; ~cents/mile for mainstream cars, rising with value (the test market's truth is ≈ $0.05/mile at ~$21k) |
| **Year** | % per model year (placeholder 7%) | Paired comps one year apart |
| **Trim/options** | $ amount from paired comps (trim difference); only count options buyers pay for | Paired comps; guide option values |
| **Condition** | % per step on your rubric (placeholder 3%/step) | Condition-matched pairs; cost-to-cure for visible defects (tires, brakes, paint, interior) |
| **Accident history** | % per reported accident (placeholder 6–7%) | Matched pairs; **severity matters** (structural/airbag deployment ≫ cosmetic) |
| **Owners** | ~1% per additional owner | Matched pairs; a weak effect after controlling for age/miles |
| **CPO / warranty** | $ premium (placeholder $1,500) | CPO vs non-CPO matched pairs; warranty value |
| **Title brand** | Large discount (§14.5) | Branded vs clean comps |
| **Service records/deferred maintenance** | Cost-to-cure | Shop quotes (tires, brakes, timing belt, fluids) |
| **Modifications** | Usually **no add** or a discount; returns to stock may cost | Enthusiast sales (BaT) for desirable mods |

### 11.3 Quality control
Flag comps with **gross adjustments above ~20% of price** (`adjust_listings()` marks `OVER-ADJUSTED`). **Rank by lowest gross adjustment** and weight accordingly (`reconcile()`).

---

## §12. Time, Season and the Asking-to-Sale Gap

1. **Drift:** estimate from your own data (regression on listing/sale date) and the wholesale index. In the test market the truth was −0.4%/month; the regression recovered −0.45%/month. In real life, cap at ±1.5%/month unless a shock is documented.
2. **Calendar year vs model year:** a car "turns a year older" in January; Jan 1 produces a visible step in many guides.
3. **Asking-to-sale:** calibrate from **sold vs original asking** on comparable cars where possible; if you have none, use 2–5% for dealers and 3–8% for private asks, then verify with a real offer.
4. **Seasonal factors:** convertibles/sports cars sell better in spring; AWD/4x4 in fall; tax-refund season lifts demand in spring.

---

## §13. Statistical (Hedonic) Cross-Check

**Model:** `ln(price) = b0 + b1·age + b2·(miles/10k) + b3·condition + b4·accidents + b5·owners + b6·months + trim dummies`. Use **one model/generation** at a time.

**When:** 50+ comparable observations. **Checks:** hold-out error (MdAPE), residual patterns (a trim or a region the model misses), sign/size sanity (older → lower, higher miles → lower, condition → higher), **treat active listings consistently** (deflate asks or include a status dummy).
**Limits:** it cannot see paint/interior quality, rust, maintenance history, modifications or cosmetic damage unless captured in your condition score; a *well-specified* model in a simulation outperforms reality. **Use it as a cross-check on comps, never alone.**

---

## §14. Guides, Special Vehicle Types and Collectors

### 14.1 Using KBB, Edmunds, J.D. Power/NADA and others
- Enter the **exact trim, options, mileage, ZIP and honest condition.** Overrated condition inflates private-party and trade-in values.
- Record **all** relevant outputs: trade-in, private-party, dealer retail; the **range**, not the midpoint.
- **Use the guide to anchor a negotiation only after validating it against local comps.**
- **Mismatches** between guides are normal; a spread of **>8–10%** signals that your inputs (trim/condition) or the model are ambiguous. Resolve with comps, not by picking the favorite.
- **Instant offers** (KBB Instant Cash Offer, CarMax, Carvana, local dealers) are *real* numbers: get 2–3, valid for days, subject to inspection (§22).

### 14.2 EVs and hybrids
- **Battery state of health (SoH)** is the key condition variable. Recharged's inspections (2,242 EVs) reported **median remaining capacity 94.9%** (average 93.9%): *fleet figures do not replace testing the specific car.* Get a **battery health report** (manufacturer app/diagnostic, OBD dongle, or a third-party battery test) and **check warranty**: manufacturer battery warranties are commonly **8 years/100,000 miles** (California requires this for zero-emission vehicle batteries; verify the specific car's terms, remaining coverage, capacity-retention guarantee and transferability).
- **Charging:** connector type (NACS/CCS/CHAdeMO), onboard charger speed, **home-charging feasibility**, public network reliability; **software/connectivity subscriptions** and feature locks; **recalls** (e.g., battery pack campaigns that reset battery warranty on some models).
- **Pricing:** used EVs had near price-parity with used gas cars in early 2026 and rose with gas prices; **EV values are policy- and news-sensitive**: use fresh comps, shorter time windows, and **wider bands (±8–10%)**.
- **Federal credits (new and used) ended Sept 30, 2025**; do not subtract one. **Hybrids** hold value well (Toyota-dominated); inspect hybrid battery/inverter service history.
- **Cold-weather range and degradation** vary; request winter range evidence if you live where it matters.

### 14.3 Trucks, SUVs, luxury, high-mileage
- **Trucks/SUVs:** towing/payload packages, diesel options and 4x4 matter; frame rust and overlanding mods are condition issues; **big negative equity** is common on 2020–2022 trucks (Tundra/Sierra/Ram trade-ins averaged **$7.4k–$8.9k underwater** in Q2 2026, Edmunds): expect sellers to be anchored to loan payoff, not value.
- **Luxury:** **steep depreciation**; out-of-warranty repair costs dominate; **get a brand-specialist PPI** and price the *maintenance liability* (air suspension, timing chains, electronics).
- **High-mileage (>100–150k):** mileage adjustment flattens; **service history, timing belt/chain, transmission fluid, rust** dominate value; buyers pay for *documented* maintenance.

### 14.4 Classic and collector cars
- **Hagerty condition grades (#1–#4):** #1 Concours (best in the world), #2 Excellent (show-winning, regional), #3 Good ("driver"), #4 Fair; **most sellers overrate the condition; most buyers do too.** Use *Hagerty Price Guide* for the condition-specific value (stock configuration), then adjust for documentation, originality, options, provenance, mileage and modifications.
- **Evidence:** auction results (Bring a Trailer, Mecum, Barrett-Jackson, RM Sotheby's) and **private-sale data** (insurance agreed values); **sold prices include buyer premiums** (e.g., BaT ~5%; auction houses ~10–12%): normalize.
- **Market state (Oct 2026):** **Hagerty Market Rating near a ~15-year low**; condition-#3 average/median values fell ~0.5% between consecutive price guides; **only ~35% of private sales trade above insured value** (lowest in ~4 years); sub-$250k values broadly softer; blue-chip trophy cars selective (⚠️ via trade-press summary).
- **PPI by a marque specialist** is non-negotiable; **provenance, matching numbers, paperwork and rust/frame condition** drive value; insure with **agreed value** and keep documentation. Import/export and registration rules (e.g., 25-year import rule) matter for certain models.

### 14.5 Branded titles, flood, lemon buybacks, modified cars
- **Salvage/rebuilt/flood/junk/lemon-law buyback** titles: the car has a different resale market and typically a **large discount** (commonly cited at 20–40% below clean-title comps, with insurance and financing difficulty; ⚠️ verify with quotes for your model). Some lenders won't finance; insurers may restrict coverage or limit to liability.
- **Flood history** can cause delayed electrical failures; **do not buy** without specialist inspection.
- **Modified cars:** sellers overvalue modifications; buyers pay for **stock**, with exceptions for desirable, professionally done, reversible work.

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
