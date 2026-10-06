---
name: homeval-diligence-risk-and-investment
description: "Use when stress-testing a specific property or deal: physical and legal due diligence (systems, title, permits, zoning, HOA, public-record lookups), climate and insurance risk as a first-order valuation input (premiums +46% since 2021, flood/wind/wildfire tools, how insurance cost converts to lost buying power), the income approach for rentals (NOI, cap rate, GRM, DSCR, cash-on-cash, negative leverage, BRRRR, the 70% flip rule, why the 1% rule fails at 7%+ rates), specialty valuations (condos, new construction, land, rural, luxury, property-tax appeals, estates), and fraud, scam and fair-housing hazards."
---

# Home Valuation and Market Research: Diligence, Risk and Investment Property

> **Part 6 of 7** of the *Home Valuation and Market Research* reference (plugin `home-valuation`), covering §26–§30. Sibling skills: `homeval-concepts-methods-and-market-structure` (§0–§4), `homeval-market-analysis-and-timing` (§5–§9), `homeval-comps-adjustments-and-avms` (§10–§15), `homeval-buyer-playbook` (§16–§20), `homeval-seller-playbook` (§21–§25), `homeval-reference` (§31–§35). Code: `scripts/homeval.py` (`noi`, `cap_rate`, `value_from_cap`, `grm`, `cash_on_cash`, `dscr`, `brrrr`, `seventy_percent_rule_max_offer`, `max_price_from_payment`).
>
> **Currency:** Diligence method is stable. Insurance and climate data are **2026 trend figures** (sources: Insurify, Cotality, Realtor.com via press; flagged); rate-dependent investment math uses **7.28%** (Oct 1, 2026) and will shift with rates.

> **⚠️ Scope.** Educational; not legal, insurance, engineering, tax or investment advice. Inspect, survey and title work must be done by licensed professionals. Rental, short-term-rental and tax rules vary by locality.

> **The three ideas:**
> 1. **⚠️ Diligence changes the price, or the decision, or nothing; it is never decoration.** Every finding should end in one of three outcomes: *credit/price change*, *repair before closing*, or *walk* (§26.3).
> 2. **⚠️ Insurance and climate risk are now valuation inputs, not footnotes.** A **+$250/month** insurance difference cuts a payment-constrained buyer's loan capacity by **~$36,500 at 7.28%**. Quote insurance *before* you commit (§27).
> 3. **⚠️ At today's rates, a "decent" rental often doesn't cash-flow.** A $360,000 rental renting at $2,400/mo (0.67% of price per month, below the 1% rule of thumb) has **DSCR 0.78 and negative cash-on-cash** with 25% down at 7.28% (§28). Underwrite on *your* financing, not on the 1% rule.

---

## §26. Physical and Legal Due Diligence

### 26.1 Systems and structure (inspection map)
| System | What to check | Red flags (price/walk) |
|---|---|---|
| **Foundation/structure** | Cracks (stair-step, horizontal), sticking doors, floor slope, crawlspace moisture, wood rot | Active movement → structural engineer before waiving contingency |
| **Roof** | Age, material, flashing, skylights, attic ventilation, decking | End-of-life roof in hail/wind regions → insurability, surcharge or non-renewal |
| **Water/drainage** | Grading, gutters, sump, basement staining, past leaks, drain-line scope | Recurrent water intrusion/mold; failing sewer lateral (scope it) |
| **Plumbing** | Supply material (polybutylene, galvanized), drain material (cast iron, Orangeburg), water heater age, pressure | Polybutylene/failing lines; water-heater leaks |
| **Electrical** | Panel brand/age, aluminum branch wiring, knob-and-tube, GFCI/AFCI, grounding | Known problem panels or wiring; unpermitted work |
| **HVAC** | Age, refrigerant type, ductwork, service history | 15–20 yr systems = near-term capital; budget for replacement |
| **Envelope** | Windows, siding, stucco/EIFS moisture, insulation, air sealing | EIFS/stucco without moisture testing; extensive window failure |
| **Site** | Septic/well (inspection, flow, bacteria), trees near foundation, easements, retaining walls | Failed septic, shared wells, large trees on lines |
| **Environmental** | Radon, lead paint (pre-1978), asbestos (older), mold, pests/WDI, previous fire or flood | Radon above action levels; active termite damage |
| **Appliances/amenities** | Age and condition | Usually negotiable; not valuation-critical |
**Use independent specialists** for sewer scope, structural engineering, roofing, HVAC, electrical and radon. A general inspection is a *screen*, not a guarantee.

### 26.2 Legal and public-record diligence (county/state sources)
| Item | Source | Why it matters |
|---|---|---|
| **Ownership, liens, mortgages, judgments, easements, deed restrictions** | County recorder/register of deeds; title commitment | Clear title is required to close; restrictions limit use |
| **Parcel facts: GLA, lot, year, tax history, sales history** | Assessor; GIS parcel viewer | Check against listing; discrepancies affect appraisals |
| **Permits (open/closed), code violations** | Building department | Unpermitted GLA and open permits hit value and financing |
| **Zoning, overlays, planned changes** | Planning/zoning; comprehensive plan; transportation projects | What can be built nearby; nonconforming status; road widening |
| **Property tax: current bill, reassessment on sale, exemptions, appeals** | Tax collector/assessor | Taxes may jump after a sale; some states cap or reset |
| **HOA/condo documents** | Management company: CC&Rs, budget, reserve study, minutes, litigation, special assessments, rental rules, insurance | **A condo is bought through its association**; weak reserves or litigation can sink financing and value |
| **Survey / boundary** | Surveyor | Encroachments, easements, fence disputes |
| **Flood zone & elevation** | FEMA Flood Map Service Center; local floodplain administrator | Lender-required flood insurance; premium impact (§27) |
| **Environmental/contamination, mineral rights** | State environmental agency/EPA databases; title | Contaminated sites; severed mineral estates |
| **Utilities/broadband** | Provider maps | Practical livability; remote work viability |

### 26.3 Convert findings into decisions
| Finding type | Typical response |
|---|---|
| Safety/structural/water/mold | Specialist report → **repair by licensed contractor before closing** or **price reduction/credit equal to bids + risk margin**; **walk if scope unknown** |
| Aging systems (roof/HVAC/water heater) | Model replacement cost over 1–5 years; request credit or price cut; check insurance consequences |
| Unpermitted work | Require permit-and-inspection cure, or remove from GLA in your valuation and price accordingly |
| Title defect | Cure before closing; do not close over unresolved liens |
| HOA red flags (reserves < funded, litigation, special assessment) | Quantify per-unit cost; ask lender about project approval; consider walking |
| Cosmetic | Ignore or negotiate lightly; don't spend negotiating capital here |
**Rule of thumb:** *request fewer, bigger items backed by written estimates*, not a laundry list.

---

## §27. Climate, Insurance and Location Risk as Valuation Inputs

### 27.1 The data (2026)
- **Average annual homeowners premium projected at ~$3,057 for 2026 (+4% after +12% in 2025); up ~46% since 2021, roughly three times inflation** (Insurify via Bloomberg/press, Mar 2026). Premiums rose in 95% of ZIP codes between 2021 and 2024 (Consumer Federation of America).
- **Cotality projects ~+8% in 2026 and +8% in 2027**; insurance is now ~**9% of the typical homeowner's total payment**, a record share (⚠️ via press summaries).
- **Florida averages roughly $8,300–$8,500** (Insurify), more than double the national average; **2025 increases exceeded 20% in six states** (e.g., Minnesota +34%, Colorado +33%, Nebraska +25%, Oklahoma +24%).
- **Climate exposure:** one analysis (Realtor.com's Hale, press) put share of housing stock facing severe or extreme risk at >6% flooding, ~18% wind and ~6% wildfire; Miami-Fort Lauderdale-West Palm Beach has ~$307B in home value at risk (≈23% of local value).
- ⚠️ **Treat these as trend indicators.** Premium levels depend heavily on state, roof age, construction, deductible and claims history. **Get actual quotes.**

### 27.2 Convert insurance into price
```python
# loan capacity lost by an extra monthly cost, at 7.28%:
extra_monthly = 250
loan_capacity_lost = extra_monthly / hv.monthly_pi(1, 7.28)    # ≈ $36,538
# +$1,000/yr premium → ≈ $12,179 of loan capacity at 7.28%
```
**Valuation logic:** an uninsurable or high-premium house must be **priced down by the capitalised extra cost** (≈ extra monthly ÷ the buyer's payment-per-dollar factor), not by an arbitrary discount. Conversely, a better insurance profile (new roof, impact windows, higher elevation) is a *price-supporting* feature.

### 27.3 Insurance checklist before you commit
- **Get at least 2–3 quotes on the specific address** (not just ZIP); ask about **roof-age rules, wind/hail percentage deductibles, water-backup coverage, replacement-cost vs ACV, ordinance and law coverage.**
- **Check claims history** (CLUE/seller disclosures) and **prior non-renewal**; ask the seller for the current policy declarations and 3-year premium history.
- **Flood:** lender-required in special flood hazard areas; the NFIP's Risk Rating 2.0 pricing is property-specific (elevation, distance to water, replacement cost); private flood may be cheaper or costlier. **Even outside the mapped zone, flood risk exists**: check history, drainage and elevation.
- **State insurers of last resort** (FAIR plans/state wind pools) exist; they can be a fallback with higher cost and lower coverage.
- **Wildfire/wind/hail:** defensible-space, roof class, shutters/impact glass can matter for both premiums and availability.
- **Tools:** FEMA Flood Map Service Center; NOAA/NWS climatology; USGS; commercial property-risk tools (First Street, Cotality). *If the Cotality connector (§33) is installed, `at-get_property_climate_risk`, `at-get_property_roof_age` and `pr-get_home_price_index_forecast` can feed this step.*

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

## §29. Specialty Valuation Situations

| Situation | Method adjustments |
|---|---|
| **Condominium** | Value the **unit + the association**: reserves (percent funded), special assessments, owner-occupancy ratio, delinquency rates, litigation, insurance master policy, financing approval (FHA/VA/conventional); comps from the **same project** first, then same-quality projects; HOA dues capitalise: $400/mo extra dues ≈ $58,500 less loan capacity at 7.28% |
| **New construction** | Cost approach cross-check; compare to *resale* comps; separate **builder incentives** from price; check lot premiums and upgrades value (upgrades rarely return cost) |
| **Land / lots** | Highest-and-best-use test; comps in $/acre or $/buildable-unit; utilities, perc test, wetlands, easements, zoning and entitlements; **land has few comps: use broader time/geography and consult a land appraiser** |
| **Rural/acreage** | Large adjustments and few comps; appraiser **geographic competency** matters; consider timber/minerals/water rights |
| **Luxury/unique** | Sparse comps; widen time and geography; use cost approach and buyer-pool analysis; **negative skew risk** for overbuilt features |
| **Historic** | Preservation restrictions, tax credits, insurance, maintenance premiums |
| **Leasehold / ground lease** | Value the leasehold interest, not fee simple; lease term and reversion matter |
| **Property-tax appeal** | Gather **recent sales of similar properties and assessment ratios**; compare your assessment per sf to peers; check **filing deadlines and format**; you argue *market value on the assessment date* |
| **Estate/divorce/litigation valuation** | Hire an appraiser with an **effective date** and **USPAP-compliant report** |
| **Insurance replacement cost** | Use a cost estimator (cost to rebuild, not market value); update annually after renovations and inflation |

---

## §30. Fraud, Scams, Bias and Ethics

| Hazard | What it looks like | Defense |
|---|---|---|
| **Wire/closing-instruction fraud** | Email "from" title/escrow/agent changing wire instructions | **Call a known number** independently to verify before wiring; never use phone numbers in the email |
| **Fake listings / rentals** | Too-cheap listing, "owner abroad", requests for deposit before viewing | Verify ownership in county records; see the unit; use known platforms |
| **Title/deed theft** | Fraudulent deed recorded to steal equity/sell; vacant lots/rentals | Monitor recorded documents (county alerts); never sign blank documents |
| **"We buy houses" / foreclosure rescue** | Pressure to sign over title or sell quickly | Read every page; use an attorney; verify license |
| **Appraisal fraud/flip schemes** | Inflated appraisals via fabricated comps | Cross-check against §15; request reconsideration with evidence if too high or too low |
| **Appraisal/valuation bias** | Lower values correlated with neighborhood demographics | Request reconsideration with strong comps; second appraisal; fair-housing complaint routes (HUD, state agency) |
| **AI-edited photos/virtual staging misrepresentation** | Photos hiding defects or inventing features | Disclose edits; buyers should visit and inspect; sellers must not conceal material facts |
| **Seller non-disclosure** | Known defects concealed | Document; consult a real-estate attorney; as-is clauses don't erase fraud liability |
| **Steering** | Agent nudging by protected-class | Use objective search criteria; report violations |
| **Over-reliance on automated estimates** | Treating an AVM or LLM as a valuation | §14 → `homeval-comps-adjustments-and-avms` |

---

## §30A. Deal-Stress Template (5 minutes)

1. Value range (§15): low / mid / high. 2. Insurance + flood: annual cost; capacity lost. 3. Major systems: replacement budget 0–5 yrs. 4. Tax after sale. 5. HOA special-assessment risk. 6. Rate sensitivity: payment at ±1 pt. 7. Rental fallback: DSCR at market rent. 8. Exit: who buys this in 5 years, at what price, with what costs (6–10%)? 9. **Verdict:** buy / buy at X / walk, with the single biggest risk named.
