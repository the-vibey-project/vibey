---
name: homeval-market-analysis-and-timing
description: "Use when researching a housing market before buying or selling: the funnel procedure (macro to metro to submarket to street), precise definitions and failure modes of months of supply, days on market, sale-to-list, price-cut share, median vs index prices, real vs nominal; how mortgage rates, insurance, taxes and inventory move the marginal buyer; segmenting tiers and property types; market-regime tables with tactics for each side; forecasting humility; and the October 2026 national snapshot (4.9 months supply, 7.28% rates, 21% price cuts, Case-Shiller +1.9% vs 3.4% inflation)."
---

# Home Valuation and Market Research: Market Analysis, Drivers and Timing

> **Part 2 of 7** of the *Home Valuation and Market Research* reference (plugin `home-valuation`), covering §5–§9. Sibling skills: `homeval-concepts-methods-and-market-structure` (§0–§4), `homeval-comps-adjustments-and-avms` (§10–§15), `homeval-buyer-playbook` (§16–§20), `homeval-seller-playbook` (§21–§25), `homeval-diligence-risk-and-investment` (§26–§30), `homeval-reference` (§31–§35).
>
> **Currency:** Method sections are stable. The §5.4 and §9.3 numbers are an **October 2026 snapshot** (NAR Aug 2026 report released Sep 10; Redfin through Sep 20; Freddie Mac through Oct 1; Case-Shiller July data released Sep 29). They will be stale within weeks; re-pull before use.

> **⚠️ Scope.** Educational, not investment or lending advice. Nobody reliably times housing markets; §9 explains what you *can* do instead.

> **The three ideas:**
> 1. **⚠️ Housing is local; national numbers are a weather report for a continent.** In July 2026 the Case-Shiller 20-city range ran from **Chicago +6.9% to Seattle −1.6%** year over year; the national index was +1.9%. A national median says almost nothing about your street.
> 2. **⚠️ Every indicator has a definition that can mislead you.** The same month produced **4.9 months of supply (NAR)** and **4.1 months (Redfin, Sep 13 week)**. Neither is "wrong": they count different things (§6).
> 3. **⚠️ Price is the lagging indicator.** Listings, price cuts, pending sales, days-to-contract and delistings move first; sale prices (and indices built from closings) trail by 1–3+ months.

---

## §5. The Market-Research Procedure (the funnel)

**Run top-down, record each answer in one line, and finish with a one-paragraph "market diagnosis."** Time budget: 2–4 hours for a serious purchase or listing.

| Step | Question | Where to look | Output |
|---|---|---|---|
| 1. **Macro** | What are rates, credit, jobs and inflation doing? | Freddie Mac PMMS, FRED, BLS, MBA applications | "Rates up/down X pts in 90 days; buyers' payment power changed Y%" (§7) |
| 2. **Metro** | Is the metro tight or loose? Appreciating or falling? | Redfin Data Center, Zillow Research (ZHVI), Realtor.com research, Case-Shiller (20 metros), FHFA HPI, local Realtors' monthly report | MOS, price-cut %, sale-to-list, DOM, YoY & 3-mo trend |
| 3. **Submarket** | Which zip/school zone/neighborhood behaves differently? | MLS stats (ask an agent for a market-area report), county sales records | Same metrics, narrower |
| 4. **Segment** | Does *your price tier and property type* differ from the average? | MLS filtered: price band ±20%, beds, SFR vs condo, new vs resale | Segment MOS & trend (§8) |
| 5. **Micro** | Street, block, school boundary, flood zone, noise, HOA | County GIS, FEMA map, school-boundary tool, a site visit at 3 times | Positive/negative adjustments to apply (§11) |
| 6. **Competition** | What is actually for sale and pending that competes *with this home*? | Active + pending in the same segment; price history; DOM | A "ceiling" and a pace-of-absorption estimate |
| 7. **Diagnosis** | Which regime (§9.1) and what does it imply for tactics? | Your notes | One paragraph + 3 actions |

**Definition of the market area:** the set of homes a typical buyer of your subject would also seriously consider (substitutes), not a political boundary. Start with a 1-mile radius, same school zone, ±20% GLA and ±15% price; widen only if fewer than ~10 closed sales in 6 months.

---

## §6. Indicators: Exact Definitions and How Each One Lies

| Indicator | Formula | Reads as | ⚠️ How it misleads |
|---|---|---|---|
| **Months of supply (MOS)** | Active listings ÷ average monthly sales | <4 seller's; 4–6 balanced; >6 buyer's (conventions; local variance is large) | **Numerator and denominator vary by source:** NAR uses total inventory ÷ closed sales pace (Aug 2026: 4.9); Redfin uses active ÷ pending pace (Sep 2026: ~4.1). Closed sales lag contracts by 30–60 days, so MOS built on closings reacts late. Compare like with like over time |
| **Absorption rate** | Monthly sales ÷ active inventory | % of inventory that sells per month; inverse of MOS | Same lag issues; misleading in seasonal turning points |
| **New listings** | Count of new listings in period | Seller supply flow | Spikes with seasons; compare YoY or seasonally adjusted |
| **Pending sales** | Contracts signed, not closed | Best near-term demand signal | Some are cancelled (cancellation rates rise in cooling markets) |
| **Days on market (DOM)** | Days from list to contract (or to close) | How fast homes sell | **Re-listing resets DOM** in many systems; ask for *cumulative* DOM (CDOM). Delistings hide failures |
| **Sale-to-list ratio** | Sale price ÷ list price | <100% = buyers negotiate | Use sale-to-**original**-list, not sale-to-last-list; cuts disguise weakness. Redfin reports ~98.6–98.7% (Sep 2026) |
| **% sold above list** | Share of sales with ratio >1 | Competition intensity | Intentional low-balling ("price to attract bids") inflates it |
| **Price-cut share** | Listings with ≥1 cut ÷ active listings | Sellers' realism gap | A *rate*, not a magnitude: 21.1% of active listings cut in the 4 wks to Sep 20, 2026 (record for September in Redfin's 2022+ records) |
| **Delisting rate** | Listings withdrawn ÷ listings | Sellers who refuse to meet the market | Not captured in price or DOM stats; a **hidden supply overhang** |
| **Median sale price** | Middle closed price | Headline stat | **Composition effect**: if more large/new homes sell, the median rises with no home gaining value (NAR itself warns of this) |
| **$/sf** | Price ÷ GLA | Size-normalised price | GLA definitions vary (ANSI Z765 vs agent-entered); finished basements/ADUs distort; not linear in size (§11) |
| **Repeat-sales index** (Case-Shiller, FHFA HPI) | Price change of the *same* houses across sales | Like-for-like appreciation | 2-month lag; metro-level; excludes new construction; not your tier |
| **Hedonic index** (Zillow ZHVI, Cotality HPI) | Model-adjusted values | Smoother; includes all homes | Model-dependent; can lag turning points |
| **Real vs nominal** | Nominal growth − CPI | Purchasing-power change | **July 2026: +1.9% nominal vs 3.4% CPI = 14th straight month of real price decline** (Case-Shiller release) |
| **NSA vs SA** | Seasonally unadjusted vs adjusted | Spring bumps ≠ trend | Compare YoY or use SA; Case-Shiller's May 2026 NSA monthly +0.6% was SA −0.05% |

**Rule:** quote every indicator with *source, definition, geography, period and whether seasonally adjusted.* If you can't, don't quote it.

---

## §7. What Moves the Marginal Buyer (the demand side)

### 7.1 Rates → payment → purchasing power
**Payment per $100,000 borrowed, 30-year fixed (principal & interest):**

| Rate | P&I per $100k | vs 6.01% |
|---|---|---|
| 5.00% | $536.82 | −10.6% |
| 6.00% | $599.55 | −0.1% |
| 6.01% (Feb 19, 2026 low) | $600.19 | — |
| 6.50% | $632.07 | +5.3% |
| 7.00% | $665.30 | +10.8% |
| **7.28% (Oct 1, 2026)** | **$684.21** | **+14.0%** |
| 7.50% | $699.21 | +16.5% |
| 8.00% | $733.76 | +22.3% |

- **A one-point rate rise (6% → 7%) raises the payment ~11%.** From 6.01% to 7.28% the same loan costs 14% more per month, so *holding the payment fixed, borrowing power falls ~12%*. In the toolkit example, a buyer with a $2,600 all-in monthly budget and 10% down could afford about **$355,000 at 6.01% but about $319,000 at 7.28%** (assumes 0.9% tax rate, $3,057/yr insurance, 0.6% PMI).
- **Why sale prices don't fall one-for-one:** (a) sellers with low-rate mortgages won't sell (the **lock-in effect**), shrinking supply; (b) buyers use rate buydowns and concessions rather than price cuts; (c) price changes ride on the *marginal* buyer, not the average one. The adjustment shows up as **fewer sales, longer DOM and more concessions first**, price second.
- **Concessions are the shadow price.** A 3% concession on a $429,100 home is $12,873; lenders cap seller concessions by loan type and LTV (verify current Fannie/Freddie/FHA/VA limits with your lender). Comps with concessions must be adjusted to cash-equivalent (§11).

### 7.2 The other payment components
- **Homeowners insurance** is now a first-order valuation input: average premiums were projected at **~$3,057 for 2026** (Insurify), up **46% since 2021** and **+12% in 2025**; Cotality projects another **~8% in 2026 and 2027** and says insurance is ~9% of a typical homeowner's payment (record high). Florida averages near **$8,300–$8,500**. Each **+$250/month** of insurance cuts a payment-constrained buyer's loan capacity by **~$36,500 at 7.28%** (§27 → `homeval-diligence-risk-and-investment`).
- **Property tax** (including reassessment on sale), **HOA**, **mortgage insurance** and **maintenance (~1%/yr of value as a planning floor)** complete the cost. Buyers qualify on PITI but *live* on all-in cost.
- **Income and employment:** price-to-income and payment-to-income ratios show structural affordability; local employer concentration is a risk (a single-industry town is a *credit event* for the housing market).

### 7.3 Supply side
- **Existing inventory:** NAR Aug 2026: **1.62M units** (highest since Nov 2019), **4.9 months**; median days on market 31 (NAR RCI).
- **New construction** competes with resale using rate buydowns; where builders are the marginal seller, resale prices cap at builder incentive-adjusted levels.
- **Investor activity:** the **21st Century ROAD to Housing Act** (enacted **Jul 11, 2026**, P.L. 119-101) prohibits *large institutional investors* (control of ≥350 single-family homes) from buying additional single-family homes, **effective Jan 7, 2027 for 15 years**, with exceptions. Small investors are unaffected; expect modest effects on the exit-buyer pool in institutional-heavy metros (⚠️ effect sizes are contested; institutional owners hold a small national share of single-family rentals, ~2–3% by GAO/Urban Institute estimates cited in press).

---

## §8. Segmentation: Never Average Across Tiers

- **Price tier:** Cotality's July 2026 read had low- and high-priced homes flat while the *middle* tier dipped. A "market is up 2%" headline can be false for your tier.
- **Property type:** condos carry HOA special-assessment and project-financing risk (reserves, owner-occupancy ratio, litigation); townhomes and detached homes trade on different buyer pools; **never mix condos and SFR in comps.**
- **Age/quality:** new construction vs 1970s resale vs historic: different buyer sets, different incentives, different inspection risk.
- **Micro-location premiums** (school boundary, flood zone, busy road, walkability) are often *larger* than any bed/bath adjustment. Quantify with paired sales (§11) rather than listing language.
- **Pricing bands:** buyers search in price bands ($400k, $450k…); a list price just above a round-number cutoff drops out of many filtered searches. Treat band edges as a **demand cliff** and test both sides.

---

## §9. Regimes, Tactics and Timing Humility

### 9.1 Regime table (the MOS cut-offs are common conventions; the sale-to-list, DOM and price-cut bands are this reference's own heuristics, not an industry standard, so calibrate locally)
| Regime | MOS | Sale-to-orig-list | DOM trend | Price cuts | Seller tactic | Buyer tactic |
|---|---|---|---|---|---|---|
| **Hot** | <3 | ≥101% | falling | <12% | Price at/just above comps; short marketing; multiple-offer protocol | Pre-underwritten financing; shorter contingencies; know your walk-away price (§18) |
| **Seller-leaning** | 3–4 | 99.5–101% | stable/falling | 12–18% | Price at best comps; strong photos; terms flexibility | Clean offers; target homes with high DOM for leverage |
| **Balanced** | 4–6 | 97.5–99.5% | stable | 18–24% | Price to the comps *on day 1* (§22) | Negotiate repairs and credits; ask for rate buydowns |
| **Buyer-leaning** | 6–8 | 95–97.5% | rising | 24–30% | Price *under* recent comps or fund concessions; pre-inspection; flexible closing | Lowball-with-reasons; request credits; longer inspection; watch stale listings |
| **Falling** | >8 | <95% | sharply rising | >30% | Realistic exit pricing; consider renting; avoid chasing the market down | Wait, or buy discount distress; beware catching knives; stress-test income |

### 9.2 Leading-indicator dashboard (check weekly)
1) Weekly pending sales (YoY) → 2) price-cut share → 3) new listings vs pending ratio → 4) median DOM to contract → 5) sale-to-original-list → 6) delistings → 7) mortgage purchase applications / rates. **Two or more moving the same way for 4+ weeks is a regime shift signal.**

### 9.3 Snapshot: United States, October 2026 (re-pull before relying)
| Metric | Reading | Source / date |
|---|---|---|
| Existing-home sales | **3.98M** annual rate (−2.0% MoM, −1.2% YoY); first month below 4M since Jun 2025 | NAR, Sep 10, 2026 (Aug data) |
| Inventory / months supply | **1.62M** / **4.9 months** ("highest in over ten years") | NAR |
| Median existing-home price | **$429,100** (+1.6% YoY; 38th straight YoY gain) | NAR |
| Redfin median sale price (4 wks to Sep 6) | $398,637 (+2.2%); median DOM **46**; sale-to-list **98.7%**; **20.8%** of listings with a cut | Redfin, Sep 10 |
| Price-cut share (4 wks to Sep 20) | **21.1%** (record for September in Redfin's series) | Redfin, Sep 30 |
| Pending sales | Lowest in ~3 years (Sep 17 report) | Redfin |
| 30-yr fixed (PMMS) | 6.01% (Feb 19 low) → 6.71% (Sep 3) → 7.03% (Sep 24) → **7.28% (Oct 1)** | Freddie Mac (Oct figure via Trading Economics) |
| Case-Shiller National (Jul) | **+1.9% YoY** (20-city **+2.5%**); **real decline for 14th straight month** (CPI 3.4%) | S&P Cotality, Sep 29 |
| Metro dispersion (Jul) | Chicago **+6.9%**, NYC +5.8%, Cleveland +4.2% … Seattle **−1.6%** | Case-Shiller |
| Strongest buyer's markets | San Antonio, Dallas, Austin (>2 sellers per buyer, Redfin); Denver has highest cut share (30.9%) | Redfin, Sep 30 |
| Seller's markets | Only ~5 metros (San Francisco among them, AI-wealth driven; cut share 9.6%) | Redfin |

**Reading it:** a **cooling, buyer-leaning national market with enormous regional dispersion**, hit by a sharp *rate* shock in September. Sellers face the price-versus-patience problem (§22); buyers have leverage but a much higher payment per dollar of price (§7.1).

### 9.4 Timing humility (what to do instead of predicting)
- **No one reliably calls turning points**, including economists; forecasts are scenarios. Use them to bracket risk, not to bet.
- **Match the decision to the horizon.** A buyer staying 8+ years should weigh *total cost of ownership and fit* above entry timing; a buyer who might move in 3 years faces transaction costs (~6–10% round trip) that dominate (§20, §21).
- **Asymmetry of regret:** you can *refinance* a high rate later (cost ~2–3% of the loan, not guaranteed); you cannot *un-overpay*. ⚠️ "Marry the house, date the rate" is only wise if you can survive the payment at today's rate with reserves.
- **Seasonality is real but modest:** spring brings more buyers *and* more competing listings; fall/winter has fewer of both. Compare your segment's historical monthly list-to-sale patterns rather than relying on folklore.
- **Sellers:** the real optionality is *price flexibility and terms*, not calendar timing (§22).

---

## §9A. Market Diagnosis Template (fill in, one paragraph)

> *"As of [date], [metro/segment] is a [regime] market. MOS is [x] ([source/definition]); median DOM [x] (CDOM [x]); sale-to-original-list [x]%; [x]% of listings have cut price and [x]% delisted; pending sales are [up/down] [x]% YoY; 30-yr rates are [x]%, ~[x]% above where they were [n] months ago, cutting purchasing power ~[x]%. Closed-sale prices in my segment are [up/down] [x]% YoY (repeat-sales index) and [x]% over 3 months (hedonic). Implication: [buyer/seller] tactics are [..]; my walk-away/floor is [..]."*
