---
name: bizval-market-analysis-and-timing
description: "Use when researching the market for buying or selling a company: the funnel procedure (macro and rates to sector to size segment to comparable deals to buyer universe to financing), indicators and how each lies (BizBuySell multiples and volume, GF Data EBITDA multiples, PitchBook/deal volume, SBA activity, Carta venture rounds, public-market multiples and equity risk premium, Fed policy and Treasury yields), drivers (cost of capital, credit availability, buyer and seller supply, earnings trend, policy), regime table with tactics for sellers and buyers, timing humility and the cost of waiting, and the October 2026 snapshot (Fed hike to 3.75-4.00%, 10-year ~5.3%, BizBuySell 2.7x SDE, GF Data 7.0x, SBA SOP 50 10 8.1)."
---

# Company and Non-Profit Valuation: Market Analysis, Drivers and Timing

> **Part 2 of 9** of the *Company and Non-Profit Valuation* reference (plugin `business-valuation`), covering §5–§9. Sibling skills: `bizval-concepts-standards-and-market-structure` (§0–§4), `bizval-valuing-a-private-company` (§10–§15), `bizval-buyer-playbook` (§16–§20), `bizval-seller-playbook` (§21–§25), `bizval-diligence-startups-public-and-disputes` (§26–§30), `bizval-nonprofit-valuation-and-transactions` (§31–§34), `bizval-nonprofit-financial-health-and-impact` (§35–§38), `bizval-reference` (§39–§43).
>
> **Currency:** Method is stable. §9.3 is an **October 6, 2026 snapshot**; rates in particular moved sharply in September. Re-pull before use.

> **⚠️ Scope.** Educational; not investment advice. No one times deal markets reliably (§9.4).

> **The three ideas:**
> 1. **⚠️ Rates are the macro variable that matters most right now, but small-deal multiples are sticky.** The Fed raised to **3.75–4.00%** on Sept 16, 2026 (first hike since 2023), the 10-year Treasury traded near **5.3%** (highest since 2002) and prime is **7.00%**. In the toolkit's DCF example, a discount rate **1.3 points lower** raises EV by **15.5%**; yet BizBuySell's average multiple held **~2.7×** while deal count fell **~10%** (§6, §9.3).
> 2. **⚠️ Volume moves before price.** In soft markets, fewer deals close and listings sit; headline multiples barely move because only the best-quality deals close ("selection"). Watch **closed volume, days on market, and the share of listings that sell**, not just averages (§6).
> 3. **⚠️ Segment, don't average.** A Main Street SDE multiple, a PE mid-market EBITDA multiple and a public-market P/E are different instruments. Size, growth, recurring revenue and concentration explain more variation than the "industry average" (§8).

---

## §5. The Market-Research Procedure (the funnel)

| Step | Question | Where to look | Output (one line each) |
|---|---|---|---|
| 1. **Macro/rates** | Fed path, 10-year, credit spreads, inflation, policy | Fed/FOMC statements, Treasury yields (FRED), CNBC/Reuters | "10-yr [x]%, prime [y]%; direction [up/flat/down]" |
| 2. **Cost of capital** | Risk-free, ERP, size and specific premia | Kroll Cost of Capital Navigator, Damodaran | "WACC for my risk class ≈ [r]%" |
| 3. **Capital availability** | Bank/SBA/private-credit terms | SBA SOP updates, lender quotes, PitchBook/LCD | "Loan: [rate], [term], [equity %]" |
| 4. **Sector** | Growth, margins, disruption, regulation | Industry data, public comps, broker commentary | "Sector [hot/steady/pressured]" |
| 5. **Size segment** | Which market does this company trade in? | §4.1 | "Segment = Main Street / LMM / MM" |
| 6. **Comparable deals** | Closed prices and terms | BizBuySell, DealStats, GF Data, broker comps | "Median [x]× [SDE/EBITDA]; IQR [..]" |
| 7. **Buyer universe** | Who can pay and why | Broker/advisor lists; PE add-on logic | "Likely buyers: [types]" |
| 8. **Diagnosis** | Regime and tactics (§9.1) | Your notes | One paragraph + 3 actions |

**Rule:** quote every indicator with *source, definition, period, population and whether averages or medians.* BizBuySell reports **voluntarily broker-reported closed deals** (≈50,000 listings/sales sampled); GF Data covers **PE-sponsored deals $1–500M EV (standard cohort $10–500M)**; Carta covers **startups on Carta**: different populations answer different questions.

---

## §6. Indicators: Definitions and How Each Lies

| Indicator | Definition | Reads as | ⚠️ Pitfalls |
|---|---|---|---|
| **BizBuySell average cash-flow multiple** | Average of sale price ÷ SDE for reported closed deals | Main Street pricing | **Average of ratios** ≠ ratio of medians (e.g., median price $349,250 ÷ median cash flow $155,921 = **2.24×**, vs reported ~2.7× average); skewed by a few high multiples; broker-reported |
| **BizBuySell volume / median price** | Closed deals; median sale price | Liquidity and size | Q2 2026: **2,117 deals (−10% YoY and QoQ)**; median price **$349,250** (−1%) |
| **Median revenue / cash flow of sold businesses** | Typical business sold | Buyer selection | **$692,087 / $155,921**, both −3% YoY: *buyers are focusing on cash flow* |
| **Days on market** | Listing to sale | Seller leverage | Earlier BizBuySell data showed median ~**155 days**; unsold listings are excluded (**survivorship**) |
| **GF Data TEV/EBITDA** | Average TEV ÷ TTM adjusted EBITDA, PE deals | Middle-market pricing | Mix-driven (e.g., Q2 2026 **7.0×** vs Q1 **7.3×** because no $250–500M deals closed) |
| **PitchBook / MergerMarket deal data** | Deal count/value | Market activity | Sources disagree (PitchBook middle-market PE deal value **+10.7% YoY**; MergerMarket North American deal volume in June **~52% below January**) |
| **Public multiples (P/E, EV/EBITDA)** | Market prices ÷ earnings | Reference only | Public ≠ private (liquidity, size, transparency); sector mix distorts |
| **Equity risk premium (ERP)** | Required return over risk-free | Cost of capital | Several definitions (implied, historical, Kroll recommended **5.0%**); simple earnings-yield-minus-10yr spread near or below zero in 2026 (§9.3) |
| **Treasury yields/Fed funds** | Risk-free rates | Discount rates, financing | **10-yr ~5.27–5.31% (Oct 5–6)**; **Fed funds 3.75–4.00%**; **prime 7.00%** |
| **SBA lending activity and rules** | Rule changes (SOP) | Main Street financing capacity | SOP 50 10 8 (June 1, 2025) restored **10% equity injection**; **8.1 effective Oct 1, 2026** |
| **Venture data (Carta, PitchBook, Cooley)** | Median pre-money, down-round share | Startup pricing | Different platforms, different samples; **dated** (§9.3) |
| **Sale-to-listing ratio / % of listings sold** | Price realization, liquidity | Overpricing | One practitioner source claims over half of listings never sell: ⚠️ unverified; use your broker's local data |

---

## §7. What Moves Prices and Deal Volume

### 7.1 The cost of capital channel
- **Discount rates:** `r = risk-free + beta × ERP + size premium + specific risk`. Kroll's recommended **US ERP is 5.0%** with a risk-free rate of **the higher of 3.5% normalized or the spot 20-year Treasury** (Kroll: reaffirmed through early 2026; **verify for later changes**, e.g., a March 2026 update on Middle East conflict). With long yields above 5%, **the risk-free component alone raised discount rates by 1+ point versus 2024–25**.
- **Financing capacity:** a buyer's **maximum price falls ~4% for each 1-point rise in the loan rate** (toolkit: $467,583 at 10% vs $509,294 at 8% for the same cash flow, 10-year term, DSCR 1.25). **SBA 7(a)** is priced off prime (7.00% now); the maximum spread above prime varies by loan size (⚠️ verify the current cap; commonly prime + 3.0% for larger loans, i.e., ~10%).
- **Sellers' reference prices are sticky:** owners anchor on past multiples, so rate shocks show up first as **fewer closings and longer marketing periods**, then as slower price drift.

### 7.2 Supply and demand for businesses
- **Seller supply:** retirement-age owners, burnout, performance pressure, tax-law deadlines.
- **Buyer demand:** individuals using SBA loans, search funds, independent sponsors, PE (**~$1.1T dry powder at year-end 2025**, a large-deal skew), strategics, family offices.
- **Quality bifurcation:** well-run, recurring-revenue, low-owner-dependence businesses transact; others sit. GF Data: **above-average performers averaged 7.1× vs 6.8× for others** (a smaller premium than before).

### 7.3 Earnings and sector trends
- **Earnings trend** dominates price: buyers pay for *trailing twelve months (TTM) and run-rate* growth. **A down year before the sale** is costly (§21).
- **Sectors:** service businesses were ~**40%** of Q2 2026 BizBuySell deals (recurring revenue, low capex); **manufacturing and restaurants** fell most (−14% and −16% in transaction value QoQ, per one summary) as buyers became selective; **software** multiples are bifurcated by growth (§28).
- **Policy and tax:** TCJA individual brackets made **permanent** by OBBBA; **100% bonus depreciation permanent** for property acquired after Jan 19, 2025; **QSBS expanded** (§24); tariffs and regulatory change affect specific sectors (⚠️ I did not verify current tariff rates).

### 7.4 Lender and process rules
- **SBA SOP 50 10 8** (effective June 1, 2025): minimum **10%** equity injection on complete changes of ownership; **seller note counts only on full standby for the life of the loan** and ≤50% of the injection; 10-year maximum amortization; $5M loan cap; partial change-of-ownership restrictions; a **March 1, 2026 notice** limited ownership/guarantor eligibility to U.S. persons (⚠️ details: verify). **SOP 50 10 8.1 (effective Oct 1, 2026):** reported to add independent-valuation and historical-earnings requirements and a **combined cap of 50% of the injection** for seller standby debt plus outside investor equity (⚠️ summarized from law-firm and advisor sources; read the SOP).
- **Effect:** more cash required from buyers, less seller-note flexibility, narrower SBA buyer pool, slower closings.

---

## §8. Segmentation: Never Average Across Segments

| Cut | What matters | Evidence |
|---|---|---|
| **Size** | **The strongest driver of multiples.** Larger EBITDA → higher multiples → broader buyer pool | In the synthetic market, the regression coefficient on ln(EBITDA) recovered **0.20** (truth 0.20): doubling EBITDA raises the multiple ~15% *holding other factors fixed* |
| **Growth / margin / recurring revenue / concentration** | Quality premium or discount | Recovered coefficients (1.0 vs true 1.2 for growth; −0.76 vs −0.9 for top-customer share) |
| **Owner dependence** | Transferability | Practitioner sources cite 10–40% "owner-dependency discounts" (⚠️ vendor-sourced); in your analysis, haircut earnings explicitly (§10, §14) |
| **Sector** | Cyclicality, capital intensity, regulation | Sector medians (e.g., manufacturing lower than all-industry in GF Data H1 2025 summaries) |
| **Deal structure** | Cash vs earnout/seller note | Headline multiples **include** deferred/contingent consideration (§18) |
| **Time** | Rates, credit | §9.3 |
**Rule:** compare like with like: *same size band, same earnings definition (SDE vs EBITDA), same period, similar growth/margin profile, comparable terms.*

---

## §9. Regimes, Tactics and Timing Humility

### 9.1 Regime table (heuristics; calibrate with local data)
| Regime | Signals | Seller tactic | Buyer tactic |
|---|---|---|---|
| **Seller's market** | Volume up, days on market short, multiples rising, cheap credit, many buyers | Run a competitive process; price at top of range; keep terms clean | Pre-arrange financing; move fast within walk-away; verify earnings |
| **Balanced** | Stable volume/multiples; moderate financing | Price to comps; invest in readiness | Negotiate structure and price; use QoE findings |
| **Selective/Frictional (Oct 2026: *volume down ~10%, multiples flat, financing tighter*)** | Fewer closings, longer timelines, buyers focus on cash flow quality, **SBA/credit hurdles** | **Sell only with clean books and reduced owner dependence;** expect structure (notes, earnouts); don't wait for a "better market" | **You have leverage on weak listings, not on good ones;** use diligence to reprice; cash buyers win |
| **Buyer's market** | Volume down >20%, multiples compressing, distressed listings | Accept structure; consider strategic buyers | Be patient; look for forced sellers; protect with escrows |

### 9.2 Leading indicators (check monthly while active)
1) 10-year yield and prime; 2) SBA/lender term changes; 3) BizBuySell/GF Data quarterly releases; 4) your broker's local days-on-market and offer-to-ask ratios; 5) public comps for your sector; 6) credit spreads/private-credit terms; 7) policy and tax-law changes.

### 9.3 Snapshot: United States, October 2026 (re-pull before relying)
| Metric | Reading | Source / date |
|---|---|---|
| **Fed funds** | **3.75–4.00%** after a **25 bp hike on Sept 16, 2026** (first since 2023; unanimous per one source; next FOMC Oct 27–28); **prime 7.00%** (effective Sept 17) | CNBC (Sep 16); PrimeRates/Mariemont (secondary) |
| **10-year Treasury** | **~5.27–5.31%** (Oct 5–6; ≈24-year high); 30-year ~5.66%; 2-year ~4.9% | CNBC Oct 5; Trading Economics Oct 6 |
| **Kroll US ERP / risk-free** | **5.0%** / higher of **3.5%** or spot **20-yr Treasury** | Kroll/BVWire (as of Sept 2025, reaffirmed Feb 2026): ⚠️ verify later updates |
| **S&P 500** | ~**7,636** at end of Sept (−1.5% MoM, +16.9% YoY); forward P/E ~**19–19.5×**; implied ERP compressed (simple earnings yield ≈ at or below 10-yr) | OANDA, Morgan Stanley GIC, others (secondary) |
| **BizBuySell Q2 2026** | **2,117** closed sales (−10%); average CF multiple **~2.7×** (reported 2.65–2.7×); median price **$349,250**; median cash flow **$155,921**; median revenue **$692,087**; revenue multiple **~0.7×** | BizBuySell via multiple summaries |
| **GF Data (PE, $10–500M EV)** | **7.0×** Q2 2026; **7.3×** Q1; **7.1×** H1 (7.2× in 2024 and 2025); 85 deals/quarter; H1 volume on pace ~**+10%** vs 2025 | GF Data via Windes/ACG (Sep 2026) |
| **PE/credit** | Middle-market PE deal value **+10.7% YoY**, exits **+14%** (PitchBook, via Valuation Research); higher-for-longer rates weigh on volume; private credit is the reference lender | Valuation Research summary (Q2 2026) |
| **SBA** | SOP 50 10 8 (June 2025) + **8.1 (Oct 1, 2026)**; 10% equity injection; seller-note standby ≤50% of injection; reported cumulative 7(a)+504 limit **$10M** from July 4, 2026 (⚠️ single source) | Law-firm/advisor summaries |
| **Venture** | Dated: Carta median pre-money **seed ~$15M, Series A ~$49M (Q3 2025), B ~$115M, C ~$254M, D ~$545M** (Carta's trailing-6-month figures); down rounds ~**17%** (Q3 2025); Cooley Q1 2026: **11.4%** down rounds | Carta; Cooley via secondary: ⚠️ no 2026 Carta quarter found |
| **Tax** | QSBS: 3/4/5-year exclusions 50/75/100%, $15M cap, $75M asset test (post-July 4, 2025 stock); 100% bonus depreciation permanent; LTCG 0/15/20% + 3.8% NIIT | OBBBA summaries (CPA/law firms) |
**Reading it:** financing costs have jumped; **volume is down, prices are flat, quality is rewarded.** Sellers face fewer, more demanding buyers; buyers face higher required returns but also weaker competition for average businesses. **Do not conclude prices will fall:** historically, volume absorbs shocks first, and multiples in small deals are sticky.

### 9.4 Timing humility and the cost of waiting
- **"Wait for a better market" is rarely a plan.** A business that waits risks (a) **earnings erosion** (the largest effect), (b) **owner fatigue**, (c) **competition from a growing pool of listings**, (d) rate or tax shocks. Use `bizval.deal_pv()`: a delayed closing with a structured price loses value through discounting (§18).
- **For sellers: sell on a rising TTM** (§21); **a flat or declining last year costs more than any macro move.**
- **For buyers: don't try to time rates; underwrite at today's rate with a margin of safety** (DSCR ≥1.25–1.5, equity cushion), and treat refinancing as upside.
- **Scenario ranges:** value at **±1 point of discount rate** and **±1 turn of multiple** (§12, §15).

---

## §9A. Market Diagnosis Template (one paragraph)

> *"As of [date], [segment] deal markets are [regime]. The 10-year is [x]% and prime [y]%; Kroll ERP [z]%, implying a discount rate near [r]% for [risk class]. Closed volume is [±%] with multiples [~flat]; comparable deals price at [median]× [SDE/EBITDA] (IQR [..]). Financing: [SBA/bank/private credit] at [terms]. For this company, size/growth/recurring-revenue/concentration suggest [above/below] median. Implication: [seller/buyer] tactics are [..]; walk-away is $[..]."*
