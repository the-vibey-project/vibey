---
name: carval-reference
description: "Use when correcting a car-valuation or car-market misconception, checking what moved (Manheim 206.2 and the first YoY decline of 2026, new ATP $50,089, used average $27,239, record negative equity, federal EV credits ended Sept 30 2025 and the used-EV rebound, auto-loan interest deduction, FTC CARS Rule withdrawn, Hagerty collector market near a 15-year low), finding primary data sources and the canon (Akerlof's lemons), or needing formulas (payment, OTD, lease money factor, rebate vs low APR, TCO), thresholds, a question-to-section picker, red flags and the method/confidence notes behind this reference. Companion to the other car valuation skills."
---

# Car Valuation and Market Research: Misconceptions, What Moved, Canon and Quick Reference

> **Part 7 of 7** of the *Car Valuation and Market Research* reference (plugin `car-valuation`), covering §31–§35. Sibling skills: `carval-concepts-methods-and-market-structure` (§0–§4), `carval-market-analysis-and-timing` (§5–§9), `carval-valuing-a-specific-vehicle` (§10–§15), `carval-buyer-playbook` (§16–§20), `carval-seller-playbook` (§21–§25), `carval-diligence-risk-and-ownership-economics` (§26–§30). Section numbers are shared across the set; §N → `skill` points into a sibling.
>
> **Currency:** §32 is verified **October 6, 2026** and is the part that dates fastest. Valuation method (§1–§2, §10–§15) is stable.

> **⚠️ Scope.** Explanatory reference; **not legal, tax, lending, insurance or mechanical advice.** Rules vary by state; figures come from sources of uneven quality (§35).

---

## §31. Misconceptions

| Misconception | Correction |
|---|---|
| The KBB/Edmunds number is what I'll get | ⚠️ **A guide is an estimate under assumptions; only a signed offer or a sale is a price** (§1, §14.1) |
| An advertised price is the price | ⚠️ **Asks convert to sales at a discount; and ads often exclude fees/add-ons. Get itemized OTD** (§10.2, §18.2) |
| Average price of same-model listings = my car's value | ⚠️ **Median error 4.4% (90th pct 12%) in the tested market vs 1.1% (3.1%) for adjusted comps** (§15.3) |
| A clean Carfax means a clean car | ⚠️ **It shows reported events only; do a PPI** (§26.2) |
| "Certified" always means manufacturer CPO | ⚠️ **Dealer-certified ≠ manufacturer-CPO; ask for the checklist and warranty in writing** (§16.3) |
| I have 3 days to return a car | ⚠️ **No federal cooling-off right for dealer car sales; return windows are company policy** (§4.2) |
| "As is" means I have no recourse | ⚠️ **It limits warranty claims, not fraud or misrepresentation** (§4.2, §25.8) |
| Dealer add-ons and fees are mandatory | ⚠️ **Only taxes/government fees (and usually the destination charge) are; negotiate the OTD** (§18.2) |
| The doc fee is a government fee | ⚠️ **It's a dealer charge; capped in some states ($85 in California), $300–$1,000+ elsewhere** (§4.3) |
| The monthly payment is what matters | ⚠️ **It can be engineered by term and add-ons; compare OTD, APR and total interest** (§16.2) |
| A longer loan saves money | ⚠️ **84 months at 8.5% cost $10,403 in interest vs $4,357 at 48 months/6.5% (on $31,500)** (§16.2) |
| 0% financing is free | ⚠️ **It usually replaces a cash rebate; at a 7% market APR a 0% offer beat a $3,000 rebate by $3,018, but a 3.9% offer lost to the rebate by $562** (§34.1) |
| Trade-ins are always a rip-off | ⚠️ **In states taxing net of trade-in, the tax credit narrows the gap; private sale beat trade-in by only ~$312 net in the example** (§22.2) |
| Negative equity disappears when I trade | ⚠️ **It's rolled into the new loan; the Q2 2026 average $6,884 added about $118/month** (§20.2) |
| Low mileage always means better | ⚠️ **Age, storage, seals, rust and maintenance matter; a documented high-mileage car can beat a neglected low-mileage one** (§14.3) |
| Leasing is always cheaper | ⚠️ **Lower payment, no equity; buying won in the example because the residual (58%) was below real value (70%)** (§28.2) |
| EV batteries die at 8 years | ⚠️ **Inspections found median battery health ~94.9% on used EVs (fleet average; test each car)** (§14.2) |
| The EV tax credit still applies | ⚠️ **Federal new and used EV credits ended Sept 30, 2025** (§4.4) |
| EV values crash after the credit ended | ⚠️ **Used EV prices rose in 2026 (avg listing $37,441, +8.2% YoY), though the segment is volatile and sources conflict early in the year** (§8) |
| Used prices fall when new prices fall | ⚠️ **They're linked through payments and substitution, but wholesale supply and financing dominate in the short run** (§7) |
| Modifications add value | ⚠️ **Rarely; buyers pay for stock** (§14.5) |
| Salvage/rebuilt cars are fine if they drive well | ⚠️ **Financing/insurance are restricted and resale is poor** (§26.3) |
| CPO doesn't need a PPI | ⚠️ **It still does** (§19.2) |
| Everyone should buy new for the low-rate promos | ⚠️ **Compare rebate vs APR and total cost; the used market can win on total cost** (§16.3) |
| The best time to buy is the last day of the month | ⚠️ **Anecdotal; use inventory/days-on-lot and OTD competition** (§7.4A) |
| The insurer's total-loss offer is final | ⚠️ **Dispute with comps and receipts; use the appraisal clause** (§25.3) |
| Classic cars always appreciate | ⚠️ **Hagerty's Market Rating hit a ~15-year low in 2026; most sub-$250k values are soft** (§29.3) |
| An LLM can tell me what my car is worth | ⚠️ **Without sales data it fabricates; use it for structure and calculations** (§14) |

---

## §32. What Moved (verified October 6, 2026)

| Topic | Change | Confidence / source |
|---|---|---|
| **Wholesale** | Manheim index **206.2** mid-Sept (−1.0% MoM, **−0.4% YoY: first YoY decline of 2026**); Aug 208.2; Jul 210; Jun 212.9; **Mar peak 215.3 (+6.2% YoY)**; MMR 3-yr-old index −0.8% since Sept 1 | High (Cox Automotive, Sep 18 and Q2/July releases) |
| **Cox year-end outlook** | MUVVI to finish 2026 ~+2% vs year-end 2025 (set mid-year; spring was stronger than expected) | Medium: may be revised; current reading is below the implied path |
| **New-vehicle prices** | ATP **$50,089** (Aug; +1.9% YoY); average MSRP $51,852; incentives 6.5% of ATP (down from 7.2%); new EV ATP **$54,813** (−2.7% YoY); inventory 2.68M | High (KBB/Cox, Sep 10) |
| **Used prices** | Average used sale **$27,239** (highest since Dec 2022); dealer used supply 44 days | High (KBB) |
| **Loans** | New avg **$43,610 / $765 / 69.5 mo**; used **$27,852 / $542 / 67.9 mo**; approvals ≈ three-quarters (easiest since 2015 per KBB) | Medium: Experian via secondary summary; KBB |
| **Negative equity** | **29.6%** of trade-ins (Q2); avg **$6,884** (record for a Q2); those buyers pay **$944/mo** vs $777; projected interest **$16,270** vs $9,811 | High (Edmunds press release, Jul 16) |
| **Credit stress** | Serious-delinquency flow **3.00%** of balances (vs 2.93%); balances **$1.71T** | Medium (NY Fed via secondary) |
| **EV credits** | **Federal new ($7,500) and used ($4,000) EV credits ended Sept 30, 2025** (OBBBA); new EV sales fell sharply (~−28% in Q1 2026); **used EVs rose in value** (listing **$37,441**, +8.2% YoY; wholesale +12.4% YoY mid-July vs gas +1.1%) | High on the end date; **medium** on used-EV magnitudes (secondary, conflicting early-2026 data) |
| **Gas prices** | ≈ **$4.10/gal** late July (~+31% YoY) per Cox commentary | Low-medium (secondary) |
| **Auto-loan interest deduction** | Up to **$10,000/yr** for **new, US-assembled** personal-use vehicles, **2025–2028**, income phase-out ($100k/$200k MAGI start); used/lease excluded; IRS guidance reported finalized Sept 2026 | Medium-high; ⚠️ verify IRS rules and state conformity (most states haven't conformed) |
| **FTC CARS Rule** | **Vacated Jan 27, 2025** (Fifth Circuit, procedural); **formally withdrawn Feb 12, 2026** | ⚠️ Withdrawal date from a single practitioner source; vacatur widely reported |
| **Dealer fees** | Doc fees: national averages ~$300–$510 across studies; FL ~$999; CA $85 cap; add-ons ~$2,000 per deal (one vendor dataset) | Medium: vendor datasets disagree |
| **Depreciation** | 5-year average **41.8%** (improved 3.8 points vs prior year); trucks/hybrids best; EVs and luxury dominate the worst list | High (iSeeCars, Mar 2026) |
| **Collector cars** | Hagerty Market Rating near a ~15-year low; condition-#3 values −0.5% book-to-book; only ~35% of private sales above insured value | Medium (Hagerty via trade press) |

**Not verified / open:** current tariff rates and their price pass-through; any post-Oct 6 data; state-by-state sales-tax, title and lemon-law changes; the exact IRS guidance for the loan-interest deduction; KBB/Edmunds method changes; battery-warranty specifics by model; current used-loan APR (sources conflicted: ~6.4–7% prime new-loan averages vs higher figures for used/subprime).

---

## §33. Canon and Data Sources

**Theory and evidence**
| Source | Why |
|---|---|
| **Akerlof (1970), "The Market for 'Lemons'," *QJE*** | The foundational paper on adverse selection in used cars (why asymmetric information depresses prices) |
| **Bond (1982, *AER*)**, used pickup trucks; **Genesove (1993, *JPE*)**, wholesale used cars | Empirical tests: the lemons effect is weaker or context-dependent in practice |
| **FTC Used Car Rule (16 CFR Part 455)** | The Buyers Guide requirement and as-is rules |
| **Federal Odometer Act (49 U.S.C. ch. 327)** | Odometer disclosure and tampering law |
| **Hagerty Price Guide / Valuation Tools** | Condition-graded collector values and auction data |

**Free/public data (check definitions every time)**
| Source | Use |
|---|---|
| **Cox Automotive Insights** (coxautoinc.com/insights) | Manheim Used Vehicle Value Index, mid-month and monthly; KBB ATP reports |
| **Kelley Blue Book** (kbb.com; mediaroom.kbb.com) | ATP, used prices, instant cash offers, cost to own |
| **Edmunds** (edmunds.com; press room) | Negative equity, transaction data, True Cost to Own |
| **iSeeCars** (iseecars.com) | Model-level depreciation and resale studies |
| **Experian Automotive; NY Fed Household Debt and Credit** | Loan size, terms, delinquency |
| **FRED** (fred.stlouisfed.org): e.g., `TOTALSA`, `CUSR0000SETA02` | Vehicle sales and used-car CPI (confirm series IDs) |
| **NHTSA** (recall lookup by VIN; ratings) | Recalls and safety |
| **NMVTIS / NICB VINCheck** | Title brands, theft/salvage checks |
| **IIHS; Consumer Reports; J.D. Power** | Safety and reliability |
| **FTC consumer advice; CFPB; state AG** | Rights, scams, complaints |
| **fueleconomy.gov** | MPG/EV efficiency data for running-cost calculations |

**Optional connector:** **CarGurus** (listing search and detail; authless). If you install it, `vehicle-listing-search` and `vehicle-listing-detail` can supply live local comps for §10; asking prices only, so apply §12 adjustments.

---

## §34. Quick Reference

### 34.1 Formulas
```
Loan payment       = P · r / (1 − (1+r)^−n),  r = APR/12
Total interest     = payment · n − P
OTD price          = vehicle + doc fee + add-ons + sales tax + title/reg − trade − rebates
Sales tax (net-of-trade states) = rate × (vehicle + doc + add-ons − trade)   (verify your state's base)
Lease payment      = (cap − residual)/n + (cap + residual) × MF ;   APR ≈ MF × 2400
Residual           = MSRP × residual%;  Cap cost = price − cap reduction + fees
Rebate vs APR      → compare TOTAL cash paid: down + payments (rebate: loan at your market APR; promo: loan at promo APR)
Adjusted comp      = Price + Σ adjustments (comp → subject; superior comp → subtract)
Mileage adj        = (comp miles − subject miles) × $/mile
Equity             = market value − loan payoff  (negative = underwater)
TCO per mile       = (depreciation + interest + taxes/fees + running) ÷ miles
Cost of waiting    ≈ monthly depreciation % + monthly market drift % (plus carrying costs)
EV $/mi            = kWh/mi × blended $/kWh ;  gas $/mi = $/gal ÷ mpg
```

### 34.2 Thresholds (heuristics; calibrate locally)
| Item | Value |
|---|---|
| Comps | 6–10 (≥3 sold); same trim; year ±1; miles ±20–25k; 100–250 mi; ≤60–90 days |
| Adjustment QC | Flag gross adjustments > ~20% |
| Asking → sale | 2–5% dealer; 3–8% private (placeholders; calibrate) |
| Used days' supply | <35 hot; 35–55 firm/balanced; >55 soft; >70 falling |
| Mileage bands | 60k / 100k / 150k (listing-filter cliffs) |
| PPI | ~$100–$250; always for used (incl. CPO) |
| Repair vs replace | Repair if < ~50% of value and root-cause fix |
| 20/4/10 | ≥20% down, ≤48 months, total transport ≤10% of gross (guardrail only) |
| Funds verification | Never release title/keys until funds are cleared at the bank |
| Closing documents | Bill of sale ×2; title signed correctly; odometer statement; **release of liability** filed |

### 34.3 Picker
| Question | Go to |
|---|---|
| What does "value" mean here? | §1–§3 |
| What are my rights as a car buyer? | §4.2, §30 |
| Is it a good time to buy/sell? | §5–§9, §32 |
| What's this car worth? | §10–§15 |
| Should I trust KBB/Edmunds? | §14.1 |
| EV battery/used EV | §14.2, §28.3 |
| Classic/collector | §14.4, §29.3 |
| What do I offer / how do I negotiate? | §18 |
| Financing, term, negative equity | §16.2, §20.2 |
| Dealer fees and add-ons | §4.3, §19.1 |
| Private-party purchase steps | §19.3 |
| Sell: which channel? | §22 |
| Sell: paperwork and scams | §24 |
| Inspection/history/title | §26 |
| Fraud patterns | §27 |
| TCO, lease vs buy, EV vs gas, repair vs replace | §28 |
| Lemon law/complaints/repo | §30 |

### 34.4 Red flags (any three = slow down)
- [ ] Price far below comps; no VIN; seller won't allow a PPI
- [ ] Name on title ≠ seller; "title in the mail"; lien not disclosed
- [ ] History shows brand/odometer anomaly; wear doesn't match mileage
- [ ] Dealer won't give an itemized OTD in writing; add-ons "required"
- [ ] Monthly-payment-only negotiation; 84-month term; negative equity rolled in
- [ ] Spot delivery with "pending financing"
- [ ] Buyer overpays, wants a courier, or uses payment screenshots/escrow they propose
- [ ] EV with no battery report; hybrid with unknown service history

---

## §35. Method

**Stable material** (valuation framework, adjustment logic, loan/lease/TCO arithmetic, consumer-protection basics) comes from established appraisal and finance practice. **Dated material** (§9.3, §32) comes from searches run **October 6, 2026**.

**Confidence.**
- **High:** valuation framework; Manheim, KBB ATP, Edmunds negative-equity and iSeeCars figures (primary releases); end date of the federal EV credits; all arithmetic (computed and tested).
- **Medium:** Experian loan figures and NY Fed delinquency (secondary summaries); used-EV magnitudes (sources conflict); doc-fee averages and add-on totals (vendor datasets); the auto-loan deduction details; Hagerty summaries (trade press).
- **Low / unverified (flagged inline):** the FTC CARS Rule withdrawal date (single source); gas-price figure (secondary); tariffs; state-specific rules; per-model battery warranties.

**Source quality.** Many 2026 sources on fees, EV values, depreciation and "how to negotiate" are **dealer-data vendors, lead-generation sites or content marketing**: informative, but commercially motivated and sometimes recycling older vintages. I preferred Cox/Manheim, KBB, Edmunds, iSeeCars, the FTC and law-firm/trade summaries, and flagged the rest.

**Three deliberate choices.**
1. **Error bars and adjustments before answers.** The skill leads with *how wrong a naive number is* (4.4% median, 12% at the 90th percentile) and how adjusted comps fix it, because single-number "book value" thinking is the characteristic failure of both buyers and sellers.
2. **Tested code, synthetic truth.** The worked example uses simulated sales so accuracy can be *checked*: adjusted comps 1.1%, regression 1.1%, triangulated 0.7% median error over 120 subjects. ⚠️ **Real data is noisier** (unobserved condition and history; messier listings), and the simulated regression matches the data-generating process, so **expect 2–3× larger errors in practice.**
3. **Dated facts quarantined.** Market, rate and rule-dependent claims sit in §4.3–§4.4, §9.3 and §32 so the durable method in the other sections doesn't rot. **When this reference is next refreshed, update §32 first.**
