---
name: carval-market-analysis-and-timing
description: "Use when researching the car market before buying or selling: the funnel procedure (macro to segment to model to local to live competition), definitions and failure modes of the Manheim Used Vehicle Value Index, MMR, average transaction price, days' supply, incentives, loan APR/term/approval, negative-equity share; drivers (rates, new-car prices, off-lease supply, gas prices, tax-refund season, EV credit end, tariffs); segment divergence (EVs, hybrids, trucks, luxury); seasonality; regime tables with tactics for each side; cost-of-waiting math; and the October 2026 snapshot (Manheim 206.2, new ATP $50,089, used average $27,239, used EV listing $37,441, 5-year depreciation 41.8%)."
---

# Car Valuation and Market Research: Market Analysis, Drivers and Timing

> **Part 2 of 7** of the *Car Valuation and Market Research* reference (plugin `car-valuation`), covering §5–§9. Sibling skills: `carval-concepts-methods-and-market-structure` (§0–§4), `carval-valuing-a-specific-vehicle` (§10–§15), `carval-buyer-playbook` (§16–§20), `carval-seller-playbook` (§21–§25), `carval-diligence-risk-and-ownership-economics` (§26–§30), `carval-reference` (§31–§35).
>
> **Currency:** Method is stable. The §9.3 numbers are an **October 2026 snapshot**: Manheim mid-September (published Sep 18), KBB August ATP (Sep 10), Edmunds Q2 negative equity (Jul 16), Cox used-EV data (Aug/Sep), iSeeCars (Mar 2026). They go stale within weeks; re-pull before using.

> **⚠️ Scope.** Educational, not investment or financing advice. Nobody times used-car prices reliably; §9.4 explains what to do instead.

> **The three ideas:**
> 1. **⚠️ Wholesale leads, retail follows.** Dealers buy at auction (Manheim) and price retail off that cost; when the Manheim index turns, listing prices typically follow with a lag of weeks to a couple of months. Watch wholesale and *days' supply* before sticker prices.
> 2. **⚠️ "The used-car market" does not exist; segments diverge.** In Aug 2026 Manheim reported compact cars and EVs up year over year while SUVs, pickups and midsize cars were down and the overall index was flat. Always value *your segment* (§8).
> 3. **⚠️ The payment, not the price, clears this market.** Rates, term length and loan approvals determine what buyers can afford; record negative equity and 70–84 month loans mean many buyers are payment-constrained (§7).

---

## §5. The Market-Research Procedure (the funnel)

| Step | Question | Where to look | Output (one line each) |
|---|---|---|---|
| 1. **Macro** | Rates, credit availability, gas prices, consumer stress, tariffs/policy | Fed/NY Fed, Experian/Edmunds loan data, EIA/AAA gas, news | "Financing is [easier/tighter]; gas $X; stress indicators [ ]" |
| 2. **Wholesale** | Which way is the wholesale market moving? | Cox/Manheim MUVVI (mid-month and monthly), MMR 3-year-old index, Cox wholesale days' supply | "MUVVI [x] (±% MoM, ±% YoY)" |
| 3. **Retail/new** | New-car prices, incentives, inventory (substitutes and cap on used) | KBB ATP report, Cox inventory | "New ATP $X, incentives Y% of ATP, inventory Z" |
| 4. **Segment** | Body style/powertrain/price tier | Cox segment tables, iSeeCars, Recurrent (EVs), Hagerty (classics) | "My segment is [up/down] vs market" |
| 5. **Model & trim** | Depreciation, supply, redesign, recalls, reliability | iSeeCars model depreciation, NHTSA recalls, owner forums | "5-yr retention ~[x]%; redesign due [ ]" |
| 6. **Local** | Regional prices, days on lot, price cuts | CarGurus/Autotrader/Cars.com filters (radius 100–250 mi), local dealer feeds | "Local median asking $X; DOM Y; Z% cut" |
| 7. **Competition** | The 5–10 cars that actually compete with yours/target | Live listings, **sold** where available | "Best alternative costs $X all-in" |
| 8. **Diagnosis** | Regime and tactics (§9.1) | Your notes | One paragraph + 3 actions |

**Definition of "local":** for common used cars, **100–250 miles** is the relevant radius (buyers and online retailers move cars across state lines; the *tax and fee* differences can outweigh the price difference for distant cars). For rare/high-value cars, widen to national and use **transport cost** as the adjustment.

---

## §6. Indicators: Definitions and How Each Lies

| Indicator | Definition | Reads as | ⚠️ Pitfalls |
|---|---|---|---|
| **Manheim Used Vehicle Value Index (MUVVI)** | Monthly **wholesale** price index, **adjusted for mix, mileage and seasonality**; base Jan 1997 = 100 | Direction of wholesale prices | Not predictive for any individual car; adjusts for mix so it can differ from raw averages; mid-month reading is preliminary |
| **Non-adjusted wholesale prices** | Raw average auction price | What dealers actually paid | Distorted by mix (age/mileage of cars sold) |
| **MMR (Manheim Market Report)** | Wholesale value for a VIN-level vehicle | What a dealer can pay | Needs access; condition & region adjustments |
| **MMR 3-Year-Old Index** | Wholesale price index for 3-year-old cars | Early read on the "best-selling" age cohort | Cohort-specific |
| **Average transaction price (ATP), new** | Average price paid (KBB) | New-car price level | Mix-driven (more SUVs/trucks raise it); **Aug 2026: $50,089** |
| **Incentives as % of ATP** | Average discount spend | Pressure on new prices | 6.5% in Aug 2026 (down from 7.2% a year earlier) |
| **Average used sale price** | Average used transaction (KBB) | Used price level | Mix-driven; **$27,239 (Aug 2026)** |
| **Days' supply** | Inventory ÷ daily sales | Tightness (lower = tighter) | Definitions differ for new/used and by source; KBB: **44 days** used (Aug 2026) |
| **Average listing price** | Dealer asking price | Asking level | Asking ≠ selling (§10) |
| **Loan APR / term / amount** | Experian/Edmunds/Fed data | Affordability | Averages hide the subprime tail; Experian Q2 2026: new loan **$43,610 at $765/mo over 69.5 months**, used **$27,852 at $542/mo over 67.9 months** (⚠️ Experian via secondary summary) |
| **Loan approval rate** | Share of applications approved | Credit availability | KBB (Aug 2026): lenders approved about three-quarters of applications ("easiest since 2015") |
| **Negative-equity share** | % of trade-ins with loan > value | Household stress; rollover risk | Edmunds Q2 2026: **29.6%** underwater, average **$6,884**, avg age 4.0 yrs |
| **Delinquency** | Serious delinquency flow into 90+ days | Credit stress | NY Fed Q2 2026: **3.00%** of balances (vs 2.93% a year earlier), balances **$1.71T** (⚠️ secondary) |
| **EV/hybrid share and prices** | Cox EV Market Monitor, Recurrent | Powertrain segment health | EV values are policy- and gas-price-sensitive (§8) |
| **Depreciation (5-year)** | % of MSRP lost at 5 years | Resale expectation | iSeeCars: **41.8%** average (Mar 2025–Feb 2026), model dispersion huge |

**Rule:** quote every indicator with *source, definition, period and whether adjusted.* Do not compare a raw average from one source to an adjusted index from another.

---

## §7. What Moves Prices (and How to Read the Chain)

### 7.1 Wholesale → retail chain
1. **Supply entering wholesale:** off-lease returns, rental fleet turn-ins, trade-ins from new-car buyers, repos. **Model-year cohorts matter:** very low 2021–2022 new-car production created a **thin supply of 4–5-year-old cars** later; weak 2023–2024 lease volumes can thin 2026–27 off-lease supply.
2. **Dealer buying cost** (MMR) sets the retail ask. Retail asks = wholesale + reconditioning + margin (reported used-car gross margins of ~$2,000–$4,000 are cited by practitioner sources; verify).
3. **Retail demand** is set by **financing**, new-car prices and incentives (substitution), gas prices (EVs/hybrids/small cars), tax-refund season and seasonality.

### 7.2 The financing channel
- **Payment math:** at 6.35% over ~70 months, a $43,610 new loan is ~$747/month in this toolkit (Experian reports $765). **Every 1 point of APR changes a 72-month payment by ~3%;** term extensions lower payments but raise total interest (e.g., $31,500 over 48 months at 6.5% costs $4,357 in interest; 84 months at 8.5% costs $10,403).
- **Lender willingness** (approval rates), **term creep** and **rolled-in negative equity** extend demand artificially; a credit tightening reduces demand quickly for the payment-constrained segment.
- **Auto-loan interest deduction (new, US-assembled only):** small effect on aggregate demand; not a driver for used cars.

### 7.3 New-car substitution
New ATP above **$50,000**, incentives falling (6.5% of ATP), and sticker MSRP **$51,852** push buyers toward used and toward cheaper segments (subcompact SUVs and compact cars gained share in 2026). **Used prices are capped** by the new-car alternative plus the payment gap.

### 7.4 Energy and policy
- **Gas prices** (late July 2026 reported ≈ **$4.10/gal**, ~31% above a year earlier per Cox commentary via a secondary source) lift demand for compact cars, hybrids and EVs and weigh on large trucks/SUVs.
- **Federal EV credits ended Sept 30, 2025**; new-EV sales fell (~−28% YoY in Q1 2026 per Cox via secondary), new-EV prices fell, while **used EVs rose in value** (see §8).
- **Tariffs:** auto tariffs and parts costs feed new-car prices and, indirectly, used values; effects are contested and change with policy, so **verify the current tariff regime** before relying on any "tariff premium" claim (I did not independently verify 2026 tariff rates).

### 7.4A Seasonality and the calendar
- **Spring tax-refund surge:** the Manheim index peaked at **215.3 in March 2026 (+6.2% YoY)**, then normalized through summer; by mid-September it stood at **206.2**, **0.4% below Sept 2025** (first YoY decline of 2026) after a **−1.0% monthly drop vs a typical −0.3%** for September.
- **Model-year changeover (late summer–fall):** outgoing-year new cars get discounted; **a redesign** of a model depresses the prior generation's values and raises uncertainty.
- **Month/quarter-end** dealer quotas can matter for new-car deals; evidence is anecdotal and varies by dealer.
- **Weather/region:** convertibles and 4WD/AWD have regional seasonality; snow-belt vs sun-belt rust and flood exposure change condition (§26).

---

## §8. Segmentation: Never Average Across Segments

| Segment | 2026 read (Aug–Sep) | Note |
|---|---|---|
| **Overall wholesale** | Flat to slightly down YoY; fell 1% in the first half of September | Cox: normalizing after spring bounce |
| **Compact cars & EVs (wholesale)** | **Up YoY in Aug**, helped by high gas prices | Cox mid-August |
| **Midsize cars, SUVs, pickups (wholesale)** | **Down YoY** in Aug | Cox mid-August; trucks/SUVs also carry the largest trade-in negative equity ($7k–$9k at Tundra/Sierra/Ram levels) |
| **Used EVs** | Cox: average **used-EV listing $37,441 (Aug), +8.2% YoY**; wholesale used-EV values **+12.4% YoY** vs gas **+1.1%** (mid-July, via secondary); used-EV sales **+20% YoY in June** while new EV sales **−28%** | ⚠️ Secondary sources conflict on direction early in 2026 (some showed −6% YoY in March). **Segment is volatile and policy-/gas-price-driven**; Recurrent: under-$40k EVs gained, $55k+ EVs fell ~3.3% in H1 |
| **Hybrids & trucks (retention)** | iSeeCars: best 5-yr value retention among segments | Toyota dominates the hybrid list |
| **EVs & luxury (retention)** | iSeeCars: **24 of the 25 worst** 5-yr depreciators were EVs or luxury; **EV depreciation barely improved** in 2026 | New-EV price cuts depress used values |
| **Collector/classic** | Hagerty Market Rating near a ~15-year low; sub-$250k values broadly softening; blue-chip trophies selective | Different regime, different data (§14.4) |

**Other cuts that matter:** trim, drivetrain (AWD premiums by region), **mileage bands** (buyers filter at 60k/100k/150k; value cliffs sit just above those thresholds), **model year vs generation** (a pre-redesign car can be a bargain or a trap), **color** (neutral colors sell faster), **options** that buyers actually search for (driver-assist, towing, heated seats), and **title status** (brand discounts, §26).

---

## §9. Regimes, Tactics and Timing Humility

### 9.1 Regime table (thresholds are heuristics; calibrate with local data)
| Regime | Used days' supply | Wholesale trend | Listings with cuts | Seller tactic | Buyer tactic |
|---|---|---|---|---|---|
| **Hot** | <35 | Rising >1%/mo | Few | Price at market; list fast; accept good offers | Be pre-approved; decide quickly; verify condition anyway |
| **Firm** | 35–45 | Flat/up | Moderate | Price at comps; strong listing | Shop several; negotiate OTD, not monthly payment |
| **Balanced** | 45–55 | Flat | Moderate | Price to comps; expect 3–5% negotiation on asks | Compare 3+ OTD quotes; use days-on-lot |
| **Soft** | 55–70 | Falling | Many | Price sharply or take instant offer; don't wait | Wait for stale listings; lower offers justified by comps |
| **Falling** | >70 | Falling >1.5%/mo | Most | Sell now; every month costs ~1–2% | Hold cash; prices drop; beware catching knives |

### 9.2 Leading indicators (check weekly while buying/selling)
1) Manheim mid-month reading → 2) MMR 3-year-old index → 3) local days-on-lot and price-cut frequency for your model → 4) new-car incentives → 5) loan approval/APR changes → 6) gas price → 7) recall/redesign news for your model.

### 9.3 Snapshot: United States, October 2026 (re-pull before relying)
| Metric | Reading | Source / date |
|---|---|---|
| Manheim Used Vehicle Value Index | **206.2** mid-Sept (−1.0% MoM; **−0.4% YoY**, first YoY decline of 2026); Aug **208.2** (+0.4% YoY); Jul 210; Jun 212.9; **Mar peak 215.3 (+6.2% YoY)** | Cox Automotive (Sep 18, 2026; Q2 release) |
| MMR 3-Year-Old Index | **−0.8%** since the start of September (sharper than the same period last year; slightly above long-term average) | Cox, Sep 18 |
| Cox year-end outlook (set mid-year) | MUVVI to finish 2026 ~**+2%** vs year-end 2025 ("normal seasonal pattern") | Cox Q2 release ⚠️ may be revised |
| New-vehicle ATP | **$50,089** Aug (+0.5% MoM, **+1.9% YoY**); average MSRP **$51,852**; incentives **6.5%** of ATP; new EV ATP **$54,813** (−2.7% YoY); new-car inventory **2.68M** units | KBB/Cox, Sep 10 |
| Used-vehicle average sale | **$27,239** Aug (highest since Dec 2022); dealer used supply **44 days** | KBB, Sep 2026 |
| Loans (Q2 2026) | New avg **$43,610 / $765 / 69.5 mo**; used **$27,852 / $542 / 67.9 mo**; approvals ~three-quarters of applications | Experian (via secondary); KBB |
| Negative equity (Q2) | **29.6%** of trade-ins; avg **$6,884**; those buyers' new-loan payment **$944** vs **$777** average; projected interest **$16,270** vs **$9,811** | Edmunds, Jul 16, 2026 |
| Used EVs | Cox avg listing **$37,441** (Aug, +8.2% YoY); used EV share of Manheim units **>4%** record (July) | Cox/Recurrent; ⚠️ partly secondary |
| 5-yr depreciation | **41.8%** average (best: trucks/hybrids; worst: EVs/luxury) | iSeeCars, Mar 2026 |
| Collector cars | Hagerty Market Rating near **~15-year low**; condition-#3 values down ~0.5% book-to-book | Hagerty (via trade press) |

**Reading it:** wholesale values have **given back the spring bounce** and are now slightly below last year; new-car prices are rising slowly with incentives shrinking; loans are easier to get but heavily leveraged (record negative equity); **segment divergence is large** (EVs and compacts firm; trucks/SUVs soft). For **buyers**, the second half of the year is typically better than spring on used prices; for **sellers**, the spring window has passed and wholesale is drifting down, so *waiting costs money* (§9.4).

### 9.4 Timing humility (and the cost of waiting)
- **A depreciating asset rarely rewards waiting.** If wholesale is falling ~1%/month and the car loses ~1–1.5%/month in value (age/mileage/market), selling 3 months later costs ~3–5% of value plus insurance, parking and opportunity cost. Use `carval.retention_curve()` for the age effect; use the Manheim trend for the market effect.
- **For buyers, waiting works only if** you have a good alternative (current car is reliable), the market is *falling*, and financing/rates are not rising. A model-year changeover is the classic good time to buy the outgoing year new.
- **Avoid forecasting** a "used-car crash" or "spike" as a decision rule; use scenario ranges (±5%) and buy/sell at a price that works at the *low* end.
- **Mileage clocks tick:** each month of ownership adds ~1,000 miles; sell before crossing a mileage band (60k/100k).

---

## §9A. Market Diagnosis Template (fill in, one paragraph)

> *"As of [date], the [segment] used-car market is [regime]. Manheim is [x] ([±% MoM, ±% YoY]); MMR for my car is $[x] (or a dealer-bought quote of $[x]). New ATP is $[x] with incentives [y]% and [z] days of used supply. Loans: APR [a]%, typical term [t] months; approvals [easy/tight]. Local asking median for my car is $[m] with [p]% price cuts and median days on lot [d]. Implication: [buyer/seller] tactics are [..]; my walk-away/floor is $[..]."*
