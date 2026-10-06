---
name: homeval-reference
description: "Use when correcting a house-valuation or housing-market misconception, checking what moved (rates 6.01% to 7.28%, UAD 3.6 mandatory Nov 2 2026, ROAD to Housing Act, NAR settlement and private-listing fights, 2026 loan limits, price cuts at record September levels, Case-Shiller +1.9% vs 3.4% inflation, Zillow error figures, Cost vs Value 2025), finding the primary data sources and canon, or needing formulas, thresholds, a question-to-section picker, red flags and the method/confidence notes behind this reference. Companion to the other home valuation skills."
---

# Home Valuation and Market Research: Misconceptions, What Moved, Canon and Quick Reference

> **Part 7 of 7** of the *Home Valuation and Market Research* reference (plugin `home-valuation`), covering §31–§35. Sibling skills: `homeval-concepts-methods-and-market-structure` (§0–§4), `homeval-market-analysis-and-timing` (§5–§9), `homeval-comps-adjustments-and-avms` (§10–§15), `homeval-buyer-playbook` (§16–§20), `homeval-seller-playbook` (§21–§25), `homeval-diligence-risk-and-investment` (§26–§30). Section numbers are shared across the set; §N → `skill` points into a sibling.
>
> **Currency:** §32 is verified **October 6, 2026** and is the part of this reference that dates fastest. Valuation method (§1–§2, §10–§15) is stable.

> **⚠️ Scope.** Explanatory reference; **not appraisal, legal, tax, lending or investment advice.** Rules vary by state; figures come from sources of uneven quality (see §35).

---

## §31. Misconceptions

| Misconception | Correction |
|---|---|
| The Zestimate (or any AVM) is an appraisal | ⚠️ **It's a statistical estimate.** Zillow's own median error: **1.78% on-market, 7.20% off-market** (Aug 2026); half of estimates are worse (§14) |
| List price is what the house is worth | ⚠️ **It's an ask.** Sale-to-original-list is the honest benchmark (§6) |
| Assessed value is market value | ⚠️ **Different date, ratio and purpose** (§1) |
| A comp is any nearby sale | ⚠️ **Closed, arm's-length, same type, recent, adjusted to cash-equivalent** (§10) |
| Average the comps | ⚠️ **Reconcile by reliability; weight the comp needing the least adjustment** (§2, §15) |
| $/sf is a constant you multiply by size | ⚠️ **Marginal sf is worth ~30–50% of average $/sf; use elasticity** (§11, §13) |
| Renovation cost = value added | ⚠️ **Value is what buyers pay; major remodels recoup far less than cost** (§23) |
| Cost vs Value returns of 200%+ are realistic | ⚠️ **They're survey estimates; the series moved 93% → 268% on the same projects across editions** (§23.2) |
| More comps = better | ⚠️ **Fewer, better, less-adjusted comps beat many weak ones** (§10) |
| Appraisals are objective truth | ⚠️ **They're informed opinions with error and reporting standards; low appraisals can be contested with evidence** (§3, §18.4) |
| Sellers always pay the buyer's agent | ⚠️ **Not since Aug 17, 2024 rules; compensation is negotiated in a written agreement and any seller contribution is off-MLS** (§4.1) |
| The agent's fee is set by law | ⚠️ **It's negotiable, and the agreement must say so** (§4.1) |
| Months of supply is one number | ⚠️ **NAR 4.9 and Redfin ~4.1 in the same month: different definitions** (§6) |
| Median price up = homes appreciating | ⚠️ **Composition effects; use repeat-sales indices** (§6) |
| Prices must fall when rates rise | ⚠️ **Sales volume, DOM and concessions adjust first; lock-in constrains supply** (§7) |
| "I'll wait for rates to drop" is a strategy | ⚠️ **You can refinance later but can't un-overpay; also wait costs carry** (§9.4, §21.2) |
| You need 20% down | ⚠️ **3–5% conventional/FHA, 0% VA/USDA; PMI cost applies** (§16.2) |
| Pre-approval = guaranteed loan | ⚠️ **Conditional; appraisal, title and underwriting still decide** (§16) |
| Waiving the appraisal contingency is just a number | ⚠️ **You owe the gap in cash if the appraisal is low** (§18.4) |
| The 1% rule means a rental is good | ⚠️ **Screen only; underwrite DSCR at your actual rate** (§28) |
| Real estate always beats renting | ⚠️ **Depends on rent-to-price, horizon, appreciation and rate (break-even ~15 years at 3% in the example)** (§20.1) |
| Spring is always the best time to sell | ⚠️ **More buyers and more competing listings; compare your segment** (§9.4) |
| Overprice then cut | ⚠️ **First two weeks decide; visible price history anchors buyers** (§22) |
| "As-is" ends seller liability | ⚠️ **Fraud and concealment liability remain** (§4.3) |
| Home-sale profit is always taxed | ⚠️ **§121 excludes up to $250k/$500k for principal residences (2-of-5 years), not indexed** (§21.4) |
| Insurance is a minor line item | ⚠️ **~9% of payment; +46% since 2021; moves loan capacity by tens of thousands** (§27) |
| Private listings are always a seller advantage | ⚠️ **Fewer buyers see them; know what you give up** (§4.2) |
| An LLM can tell me what my house is worth | ⚠️ **Without sales data it fabricates; use it for structure only** (§14.3) |

---

## §32. What Moved (verified October 6, 2026)

| Topic | Change | Confidence / source |
|---|---|---|
| **Mortgage rates** | 30-yr fixed (PMMS): **6.01% Feb 19 → 6.43% Jul 2 → 6.71% Sep 3 → 6.95% Sep 17 → 7.03% Sep 24 → 7.28% Oct 1** | High to Sep 24 (Freddie Mac releases); Oct 1 via Trading Economics citing Freddie Mac. Confirm at freddiemac.com/pmms. First >7% since Jan 2025 |
| **Existing-home market** | Aug 2026: **3.98M** sales (first <4M since Jun 2025); inventory **1.62M** (highest since Nov 2019); **4.9 months supply** (highest in 10+ years); median **$429,100** (+1.6% YoY) | High (NAR release Sep 10, 2026; multiple outlets) |
| **Price cuts** | **21.1%** of active listings cut in 4 weeks to Sep 20 (highest September in Redfin's 2022+ records); Realtor.com: 20.8%, highest Sept since 2018 | High (Redfin Sep 30; Realtor.com via Inman) |
| **Prices (index)** | Case-Shiller National **+1.9% YoY (Jul)**, 20-city **+2.5%**; **14th straight month of real decline** (CPI 3.4%); Chicago +6.9% to Seattle −1.6% | High (S&P Cotality release Sep 29) |
| **Regional split** | Buyer's markets: San Antonio, Dallas, Austin (>2 sellers per buyer); Denver 30.9% cut share; San Francisco seller's market (AI-wealth) | Medium-high (Redfin) |
| **UAD 3.6 / URAR** | **Mandatory Nov 2, 2026** (by UCDP submission date); UAD 2.6 revisions allowed through **May 3, 2027**; legacy 1004/1073/1025/2055/1075 forms retire | High (Freddie Mac UAD FAQ; Fannie Mae; trade groups) |
| **NAR settlement rules** | In force since Aug 17, 2024: no MLS compensation offers; written buyer agreements before touring; 2026 Code of Ethics tweaks tying arbitration awards to the agreement amount | High on core rules; **medium** on 2026 details (practitioner sources) |
| **Litigation after settlement** | Proposed **$52.25M** buyer-claims settlement (Apr 10, 2026); appellate affirmation reported **Aug 19, 2026** | ⚠️ **Single secondary source**; verify on dockets |
| **Private listings / Clear Cooperation** | CCP unchanged (1 business day); Zillow LAS upheld Feb 6, rewritten Mar 17; Compass dismissed Mar 18; Zillow v. Compass/MRED filed May 12; MRED ruling (Sept 15) sent matter to arbitration | Medium-high (NAR, trade press, Zillow); **live dispute** |
| **ROAD to Housing Act** | Enacted **Jul 11, 2026** (P.L. 119-101): large institutional investors (≥350 SFH) barred from buying more single-family homes, **effective Jan 7, 2027 for 15 years** | High on enactment/threshold (Mayer Brown, Morgan Lewis, Cooley); medium on exact exceptions |
| **Loan limits (2026)** | Conforming **$832,750**; high-cost ceiling **$1,249,125**; FHA floor **$541,287** | High (FHFA) |
| **Insurance** | 2026 avg ~**$3,057** (+4%), +46% since 2021; Cotality: ~+8% in 2026 and 2027; ~9% of payment | Medium (press summaries of Insurify/Cotality) |
| **Zillow accuracy** | **1.78% on-market / 7.20% off-market** median error (refresh Aug 8, 2026); Redfin ~1.98/7.66 older | High on Zillow's own figures; vintages differ across blogs |
| **Cost vs Value** | **2025 (38th) edition**: garage door 267.7%, steel door 216.4%, stone veneer 207.9%, minor kitchen 112.9% | High for that edition; **a 2026/39th edition was not found**; check Zonda |
| **§121** | $250k/$500k unchanged; not indexed | Medium-high (multiple tax sources); bills proposed, not enacted as far as found |

**Not verified / open:** the current USPAP edition and effective dates; exact seller-concession caps by loan type; state-specific disclosure/attorney rules; any post-Oct 1 rate print; whether a 2026 Cost vs Value edition has been released; effect sizes of the ROAD Act.

---

## §33. The Canon and the Data Sources

**Valuation and appraisal**
| Source | Why |
|---|---|
| *The Appraisal of Real Estate* (Appraisal Institute) | The professional standard text for the three approaches |
| **USPAP** (The Appraisal Foundation; appraisalfoundation.org) | The ethics and performance standards; check the current edition |
| Fannie Mae Selling Guide + UAD pages; Freddie Mac Guide + UAD FAQ | How lender-grade appraisals are structured; UAD 3.6 timeline |
| Case & Shiller (1989, *American Economic Review*, "The Efficiency of the Market for Single-Family Homes") and the repeat-sales methodology | The foundation of the standard price index |
| Glaeser & Gyourko, *The Economic Implications of Housing Supply* (JEP, 2018) | Why housing supply constraints drive price dynamics |
| Levitt & Syverson (2008, REStat), agent-owned homes | Incentives in agent-intermediated sales (older, one region) |
| Shiller, *Irrational Exuberance* | Narratives and bubbles in housing |

**Free market data (check definitions every time)**
| Source | Use |
|---|---|
| NAR research (nar.realtor/research-and-statistics) | Existing-home sales, inventory, median price, Pending Home Sales Index, buyer/seller profile |
| **Redfin Data Center** (redfin.com/news/data-center) | Weekly/metro price cuts, sale-to-list, DOM, MOS (pending-based) |
| **Zillow Research** (zillow.com/research/data) | ZHVI, ZORI (rents), inventory, forecasts; Zestimate accuracy page |
| **Realtor.com Research** (realtor.com/research/data) | Weekly/monthly listing counts, price cuts, DOM |
| **S&P Cotality Case-Shiller** (spglobal.com/spdji; cotality.com) | Repeat-sales indices by metro and tier |
| **FHFA House Price Index** (fhfa.gov/data/hpi) | Conforming-loan repeat-sales index by state/metro/ZIP |
| **FRED** (fred.stlouisfed.org): `MORTGAGE30US`, `CSUSHPINSA`, `USSTHPI`, `MSACSR` | Rates, Case-Shiller, FHFA HPI, new-home supply |
| **Freddie Mac PMMS** (freddiemac.com/pmms) | Weekly mortgage-rate benchmark |
| **HUD User** (huduser.gov): Fair Market Rents | Rent floor references |
| **FEMA Flood Map Service Center** (msc.fema.gov) | Flood zones/elevation |
| **CFPB** (consumerfinance.gov) | Loan Estimate/Closing Disclosure guides, mortgage rules |
| County assessor, recorder, GIS, building department | Parcel, permits, tax, deed, easements (§26.2) |

**Optional connectors (if installed in your Claude environment):** **Cotality** (property analytics, climate risk, roof age, property characteristics, home-price index and forecast), **Yardi Matrix** (multifamily/commercial market intelligence), **TinyFish** (browser/scrape monitoring of listings and prices). Use only within the sources' terms of service.

---

## §34. Quick Reference

### 34.1 Formulas
```
Market-area MOS (NAR style)  = Active inventory ÷ (closed sales / month)          [Redfin: ÷ pending/month]
Sale-to-list                  = Sale ÷ List  (prefer ÷ ORIGINAL list)
GLA adjustment                = (Subject sf − Comp sf) × marginal $/sf   (marginal ≈ 30–50% of avg $/sf)
Adjusted comp price           = Sale + Σ adjustments (comp → subject; superior comp = negative)
Net/Gross adjustment %        = Σadj/Price ; Σ|adj|/Price      (flag net > 15%, gross > 25%)
Monthly P&I                   = L · r / (1 − (1+r)^−n),  r = APR/12, n = 360
P&I per $100k at 7.28%        ≈ $684.21       (6.01% ≈ $600.19; 7.00% ≈ $665.30)
Loan capacity lost by +$X/mo  = X ÷ (P&I per $1)   e.g. $250 → ~$36.5k at 7.28%
Cap rate  = NOI ÷ Price ;  Value = NOI ÷ Cap ;  GRM = Price ÷ Gross annual rent
DSCR      = NOI ÷ Annual debt service ;  Cash-on-cash = (NOI − DS) ÷ Cash invested
Seller net = Price − payoff − commissions − concessions − transfer − title/escrow − prep − credits − prorations
Gain (home sale) = (Price − selling costs) − (purchase + closing costs + improvements)
Waiting pays only if expected monthly price gain > (carry ÷ price)
```

### 34.2 Thresholds (conventions; calibrate locally)
| Item | Value |
|---|---|
| Market regime by MOS | <4 seller's; 4–6 balanced; >6 buyer's |
| Comps | ≥3 closed (5–6 better); ≤1 mi; ≤6 mo; GLA ±10–20% |
| Adjustment caps (guideline) | Net ≤15%, gross ≤25% of comp price |
| Maintenance reserve | ~1%/yr of value |
| Selling costs | ~6–10% of price |
| DSCR for investor loans | ≥1.20–1.25 |
| Appraisal contingency | Keep unless you can pay the gap |
| Closing Disclosure | ≥3 business days before closing |

### 34.3 Picker
| Question | Go to |
|---|---|
| What is "value" and who do I trust? | §1–§3 |
| What are the rules since the NAR settlement? | §4.1, §16.4 |
| Is the market hot or cold? | §5–§6, §9.1, §9.3 |
| What can I afford at today's rate? | §7.1, §16.1 |
| What's this house worth? | §10–§15 |
| Should I trust the Zestimate? | §14 |
| What do I offer? | §18 |
| Appraisal came in low | §18.4, §24.4 |
| What do I list at? | §22 |
| What prep is worth it? | §23 |
| How do I compare offers? | §24.3 |
| Rental/flip numbers | §28 |
| Insurance/flood | §27 |
| Condo/land/unique | §29 |
| Scam or bias | §30 |

### 34.4 Red flags (collect these; any three = slow down)
- [ ] Value claimed without comps, dates or error band
- [ ] Comps older than 6 months in a moving market, or crossing school/flood/road lines
- [ ] Gross adjustments >25% on a "key" comp
- [ ] Agent's price recommendation much higher than every closed comp ("buying the listing")
- [ ] Price history missing, relisted, or "private exclusive" without a reason
- [ ] Buyer waiving appraisal and inspection with no reserves
- [ ] Insurance not quoted before contingencies lapse
- [ ] Wire instructions changed by email
- [ ] Unpermitted work counted in GLA
- [ ] Rental pro forma using seller's rents and ignoring reassessment, vacancy and capex

---

## §35. Method

**Stable material (valuation theory, adjustments, income formulas, TRID timing, wire-fraud practice, regression practice)** is drawn from established appraisal and finance practice. **Dated material** (§4.5, §9.3, §32) comes from searches run **October 6, 2026**.

**Confidence.**
- **High:** valuation framework (§1–§2, §10–§13); UAD 3.6 dates; 2026 loan limits; NAR August data; Redfin September price-cut data; Case-Shiller July data; Zillow's own accuracy figures; payment/cap-rate/DSCR arithmetic (computed and tested).
- **Medium:** rate print for Oct 1 (secondary aggregator); NAR-settlement 2026 practice details; ROAD Act exceptions; insurance trend figures (press summaries of industry reports); AVM state-level numbers.
- **Low / unverified (flagged inline):** the Aug 19, 2026 appellate item and $52.25M fund (single source); any claim about a 2026 Cost vs Value edition; seller-concession cap table; current USPAP edition.

**Source quality.** Many 2026 sources on commissions, AVM accuracy and renovation ROI are **brokerages, lead-generation sites or content marketing**: technically informative, commercially motivated, and sometimes recycling older vintages of the same figure. I preferred NAR, FHFA, Freddie Mac, Fannie Mae, S&P, Redfin and Zillow primary releases and law-firm summaries for legislation, and flagged the rest.

**Three deliberate choices.**
1. **Error bars before answers.** The skill leads with *how wrong an estimate can be* (§14, §15.4) because overconfident point values are the characteristic failure of both amateur and AVM valuations.
2. **Tested code, synthetic truth.** The worked example uses simulated sales so accuracy can be *checked*: comps +0.38%, regression −1.54%, triangulated −0.39% against the known value. ⚠️ **Real data is noisier** (unobserved condition, quality and terms), so expect larger errors and treat the example as a demonstration of method, not a promise of accuracy.
3. **Dated facts quarantined.** Rate-, rule- and statistic-dependent claims are concentrated in §4.5, §9.3 and §32 so the durable method in the other sections doesn't rot when numbers change. **When this reference is next refreshed, update §32 first.**
