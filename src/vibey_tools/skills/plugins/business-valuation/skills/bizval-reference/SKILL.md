---
name: bizval-reference
description: "Use when correcting a company or non-profit valuation misconception, checking what moved (Fed hike to 3.75-4.00% and 10-year ~5.3%, BizBuySell 2.7x SDE with volume down 10%, GF Data 7.0x, SBA SOP 50 10 8/8.1, QSBS under OBBBA, 100% bonus depreciation, 2026 charitable-giving rules, Giving USA 2026, federal funding disruption), finding primary data sources and the canon (Damodaran, Kroll, Rev. Rul. 59-60, Akerlof), or needing formulas (SDE, WACC, DCF, DSCR, deal PV, asset vs stock, QSBS, SROI, non-profit ratios), thresholds, a question-to-section picker, red flags, and the method/confidence notes behind this reference. Companion to the other company and non-profit valuation skills."
---

# Company and Non-Profit Valuation: Misconceptions, What Moved, Canon and Quick Reference

> **Part 9 of 9** of the *Company and Non-Profit Valuation* reference (plugin `business-valuation`), covering §39–§43. Sibling skills: `bizval-concepts-standards-and-market-structure` (§0–§4), `bizval-market-analysis-and-timing` (§5–§9), `bizval-valuing-a-private-company` (§10–§15), `bizval-buyer-playbook` (§16–§20), `bizval-seller-playbook` (§21–§25), `bizval-diligence-startups-public-and-disputes` (§26–§30), `bizval-nonprofit-valuation-and-transactions` (§31–§34), `bizval-nonprofit-financial-health-and-impact` (§35–§38). Section numbers are shared across the set; §N → `skill` points into a sibling.
>
> **Currency:** §40 is verified **October 6, 2026** and dates fastest; the framework (§1–§3, §10–§15) is stable.

> **⚠️ Scope.** Explanatory reference; **not investment, tax, legal, accounting or valuation-opinion advice.** Sources are of uneven quality (§43).

---

## §39. Misconceptions

| Misconception | Correction |
|---|---|
| A business is worth "X times revenue" or a fixed industry multiple | ⚠️ **Multiples depend on size, growth, margin, recurring revenue and concentration; a regression of these explained deal multiples to 1.7% median error vs 12–16% for a median multiple** (§11.3) |
| SDE and EBITDA multiples are interchangeable | ⚠️ **2.7× SDE ≠ 2.7× EBITDA; EBITDA must deduct a market-rate replacement for the owner** (§10.1) |
| My add-backs will be accepted | ⚠️ **Only documented, non-recurring, non-operating items are; $17,500 of $35,000 survived in the example** (§10.2) |
| Asking price ≈ value | ⚠️ **Asks are marketing; many overpriced listings sit and go stale** (§22.1) |
| The headline price is what I get | ⚠️ **A $5.25M structured offer was worth ~$4.6M to the seller; an all-cash $4.3M bid was worth $4.3M** (§18.2, §22.2) |
| A seller note counts toward my SBA down payment | ⚠️ **Only on full standby for the life of the loan, ≤50% of the injection (and, under 8.1, combined with outside investor equity ≤50%)** (§19.1) |
| SBA allows zero down | ⚠️ **10% equity injection is required again (SOP 50 10 8, June 2025)** (§19.1) |
| Higher rates mean prices must fall immediately | ⚠️ **Volume falls first; small-deal multiples are sticky (volume −10%, multiple ~flat, Q2 2026)** (§9.3) |
| DCF gives the "intrinsic" answer | ⚠️ **It's a leveraged opinion on the discount rate and terminal value: TV was 65% of EV; −1.3 pts of discount rate = +15.5% EV** (§12.3) |
| A 10% WACC is fine for a small company | ⚠️ **Small private companies commonly warrant 12–25%** (§12.2) |
| Asset sales and stock sales produce the same net | ⚠️ **In the example the asset deal cost the seller $170,000 more tax; the buyer's step-up was worth ~$477,000** (§24.1) |
| QSBS needs a 5-year hold | ⚠️ **Post-July-4-2025 stock gets 50%/75%/100% at 3/4/5 years; the non-excluded portion is taxed up to 28% + NIIT; pre-OBBBA stock keeps the 5-year rule** (§24.3) |
| Minority/marketability discounts always apply | ⚠️ **They depend on the standard of value; many states' fair-value statutes exclude them** (§14.1, §30) |
| A broker's valuation is an appraisal | ⚠️ **It's an opinion of value for marketing; formal appraisals follow SSVS/ASA/NACVA standards** (§3) |
| Startups are valued by DCF | ⚠️ **They're priced by rounds, comps and dilution math; the venture method gives a sanity check** (§28) |
| A non-profit can be "sold" to the highest bidder | ⚠️ **There are no owners; assets stay charitable; any for-profit or insider element requires FMV and passes AG/IRS tests** (§31, §33) |
| Restricted funds can be used to cover a deficit | ⚠️ **They follow donor intent; misuse is a compliance and legal problem** (§31.3) |
| A high program-expense ratio means a healthy charity | ⚠️ **The example had 82% program ratio, 1.6 months of cash and 45% government revenue** (§36.4) |
| Low overhead is always good | ⚠️ **The "overhead myth" and starvation cycle: under-investment in infrastructure undermines impact** (§37) |
| SROI ratios are comparable across charities | ⚠️ **They depend on proxies, deadweight and attribution: the same program was 2.67:1 or 0.69:1** (§37.4) |
| Net assets are the value of a non-profit | ⚠️ **Book $1.40M became $1.15M unencumbered after restrictions and liabilities** (§33.1) |
| The 2026 charitable deduction rules reduce all giving incentives | ⚠️ **Itemizers face a 0.5% AGI floor and 35% cap; non-itemizers gain a $1,000/$2,000 deduction** (§35.3) |
| Record total giving means every non-profit is fine | ⚠️ **Individuals' share is near its lowest; bequests and mega-gifts drove 2025; federal disruptions hit many orgs** (§35) |
| An LLM can tell me what my company is worth | ⚠️ **Without your financials and transaction data it fabricates; use it for structure, checklists and calculations** |

---

## §40. What Moved (verified October 6, 2026)

| Topic | Change | Confidence / source |
|---|---|---|
| **Fed/rates** | **FOMC hiked 25 bp to 3.75–4.00% on Sept 16, 2026** (first hike since 2023; Chair Warsh); **prime 7.00%**; **10-yr ~5.27–5.31%** on Oct 5–6 (**highest since 2002**); 30-yr ~5.66%; next FOMC Oct 27–28 | High (CNBC; Trading Economics) / medium (PrimeRates, Mariemont) |
| **Cost of capital** | **Kroll ERP 5.0%**; risk-free = higher of **3.5%** or spot **20-year Treasury** | Medium-high (BVWire, Kroll; ⚠️ later updates possible: a March 2026 note exists) |
| **Equity markets** | S&P 500 ~**7,636** (end Sept), **forward P/E ~19–19.5×**; implied ERP compressed to near/below zero on simple spread | Medium (secondary: OANDA, Morgan Stanley GIC, others) |
| **Main Street (BizBuySell Q2 2026)** | **2,117 deals (−10%)**; avg CF multiple **~2.7×** (2.65 in some summaries); median price **$349,250**; median CF **$155,921**; median revenue **$692,087**; revenue multiple ~0.7× | High (BizBuySell via multiple summaries; broker-reported) |
| **Middle market (GF Data)** | **7.0× Q2**, 7.3× Q1, **7.1× H1**; 85 deals/quarter; H1 volume on pace ~+10% | High (GF Data via Windes/ACG) |
| **PE/credit** | Mixed: PitchBook middle-market deal value +10.7% YoY, exits +14%; MergerMarket volume down sharply from January | Medium (secondary; sources disagree) |
| **SBA** | **SOP 50 10 8 (June 1, 2025):** 10% equity injection, standby-note rules; **SOP 50 10 8.1 (Oct 1, 2026):** independent valuations, historical earnings, **50% combined cap** (standby debt + outside investor equity); U.S.-owner rules (Mar 2026 notice); **cumulative 7(a)+504 limit $10M from July 4, 2026** | Medium (law-firm/advisor summaries; ⚠️ read the SOP; the $10M limit is single-source) |
| **Tax** | **QSBS: 50/75/100% at 3/4/5 years, $15M cap, $75M assets, 28% on non-excluded 3/4-year gain** (stock issued after July 4, 2025); **100% bonus depreciation permanent**; TCJA brackets permanent | High on QSBS (multiple CPA/law sources) |
| **Startups** | Carta (Q3 2025): Series A median pre-money **$49.3M**, down rounds ~**17%**; Cooley Q1 2026: **11.4%** down; **no 2026 Carta quarter retrieved**; SaaS multiples compressed (vendor-sourced) | Medium-low (dated) |
| **Giving** | **Giving USA 2026: $617.2B in 2025** (+5.7%; +3.0% real); individuals $394.2B (64%); bequests $62.19B (**+19.7%**); foundations $117.15B; corporations $43.67B | High (Giving USA/IU Lilly) |
| **Donor tax rules (2026)** | **0.5% AGI floor** (itemizers), **35% value cap** (top bracket), **$1,000/$2,000 non-itemizer deduction**, **corporate 1% floor**, 60% cash AGI limit permanent | High (multiple sources) |
| **Non-profit stress** | ~**$49B** federal grant terminations (estimate); ~**one-third** of orgs lost/at risk of federal funding; CEP: **66%** concerned about financial stability, **30%** cut staff; NFF: **>half hold ≤3 months of cash**; merger activity rising | Medium (advisor/broker and survey summaries) |
| **Charity evaluators** | Encompass (four beacons); BBB WGA standards 8 and 9 (**65%/35%**) unchanged | Medium-high |

**Not verified / open:** current 20-year Treasury yield and any Kroll update after Feb 2026; current SBA rate caps and spreads; tariff effects; **state-specific** rules (non-competes, AG review, fair-value standards); IRS §4958 amounts after any inflation changes; 2026 venture data; Damodaran's current sector multiples; Uniform Guidance thresholds (Single Audit; indirect-rate de minimis).

---

## §41. Canon and Data Sources

**Valuation theory and practice**
| Source | Why |
|---|---|
| **Damodaran (NYU Stern), *Investment Valuation* and the free datasets** (pages.stern.nyu.edu/~adamodar) | Public multiples, ERP, betas by sector; the best free reference |
| **Pratt & Grabowski, *Cost of Capital*; Pratt & Niculita, *Valuing a Business*** | The standard private-company valuation texts |
| **Koller, Goedhart, Wessels (McKinsey), *Valuation*** | DCF practice for corporations |
| **Kroll Cost of Capital Navigator/Resource Center** | ERP, normalized risk-free rate, size premia |
| **IRS Rev. Rul. 59-60 (+77-287, 83-120)** | FMV factors; restricted stock; preferred stock |
| **AICPA SSVS No. 1; ASA, NACVA standards; ASC 820/805/350/718; IVS** | Professional standards |
| **Akerlof (1970), "The Market for 'Lemons'"** | Information asymmetry: why buyers demand verification and structure |

**Deal data**
| Source | Use |
|---|---|
| **BizBuySell Insight Report** (quarterly, free) | Main Street closed-deal data (broker-reported) |
| **DealStats / Pratt's Stats; IBBA Market Pulse; GF Data; PitchBook; Axial** | Transaction comps and market surveys |
| **SBA SOP 50 10 8/8.1; SBA Lender Match** | Financing rules |
| **Carta State of Private Markets; PitchBook-NVCA Venture Monitor; Cooley/Fenwick venture reports** | Startup pricing and terms |
| **SRS Acquiom deal-terms studies** | Earnouts, escrows, indemnity norms |
| **FRED (Treasury yields, fed funds); FOMC statements** | Rates |

**Non-profit**
| Source | Use |
|---|---|
| **Giving USA (IU Lilly Family School of Philanthropy)** | Giving totals and shares |
| **Candid (GuideStar), ProPublica Nonprofit Explorer, IRS Tax Exempt Organization Search, state AG registries** | Filings and status |
| **Charity Navigator, BBB Wise Giving Alliance (Give.org), Candid Seal** | Evaluators |
| **Nonprofit Finance Fund (State of the Sector), Council of Nonprofits, CEP (Center for Effective Philanthropy), Nonprofit Financial Commons** | Sector surveys and financial-health tools |
| **Gregory & Howard, "The Nonprofit Starvation Cycle" (*SSIR*, 2009)** | Overhead myth and under-investment |
| **FASB ASC 958; ASU 2016-14; IRS Form 990 and instructions; Treas. Reg. §53.4958-6** | Accounting and compliance |
| **SROI Network/Social Value International guidance** | SROI method |

---

## §42. Quick Reference

### 42.1 Formulas
```
SDE            = net income + owner comp + interest + taxes + D&A + one-time + personal − one-time income
Adj. EBITDA    ≈ SDE − fully loaded replacement manager
EV (multiple)  = metric × multiple (cash-free, debt-free)
Equity         = EV − debt − debt-like − NWC shortfall + cash
Ke (CAPM+)     = Rf + β·ERP + size + specific          Rf = max(3.5%, spot 20y UST) per Kroll
WACC           = E/V·Ke + D/V·Kd·(1−t)
FCFF           = EBIT(1−t) + D&A − capex − ΔNWC
Gordon TV      = CF_n(1+g)/(r−g);  EV = ΣPV(CF) + PV(TV)
Cap of earn.   = CF(1+g)/(r−g);  cap rate r−g = 1/multiple
Implied r      = CF₁/Price + g
Control prem.  = 1/(1−MD) − 1
Max price (debt)= [CF/DSCR ÷ (annual payment per $)] ÷ (1 − equity%) ÷ (1 + costs%)
DSCR           = cash flow for debt service ÷ annual debt service
Deal PV        = cash + PV(note) + p·PV(earnout) + (1−haircut)·rollover + p·PV(escrow)
Venture post   = exit·(1−dilution)/target multiple
Months of cash = cash ÷ (annual expenses/12);  LUNA = unrestricted NA − net PP&E (±)
Program ratio  = program ÷ total expenses;  cost to raise $1 = fundraising ÷ contributions
HHI            = Σ(share²)
SROI           = PV[qty × proxy × (1−deadweight)(1−attribution)(1−displacement) × decay] ÷ investment
```

### 42.2 Thresholds (heuristics; calibrate)
| Item | Value |
|---|---|
| Main Street | ~2–3.5× SDE (avg ~2.7×; IQR ~1.9–3.5× practitioner) |
| PE middle market | ~7.0–7.3× TTM adj. EBITDA (GF Data) |
| Small-company discount rate | ~12–25% |
| DLOM discussions | ~20–35% (support required; jurisdiction-dependent) |
| DSCR (lenders) | ≥1.25 (often 1.25–1.5) |
| SBA equity | ≥10% of project cost; standby note ≤50% of injection |
| Customer concentration comfort | each <15–20% |
| TV share of DCF | often 60–75% |
| Non-profit months of cash | ≥3 (3–6 if reimbursement-based) |
| Non-profit concentration | no source >30–40%; HHI <0.25 |
| BBB WGA standards | program ≥65%; fundraising ≤35% of contributions |

### 42.3 Picker
| Question | Go to |
|---|---|
| What does "value" mean here? | §1–§3 |
| Which market is my company in? | §4.1 |
| Is it a good time to sell/buy? | §9 |
| What's it worth? | §10–§15 |
| What's the right discount rate? | §12.2 |
| What can I afford to pay/borrow? | §16.2, §19 |
| How do I compare offers? | §18.2, §22.2 |
| How should I structure for tax? | §24 |
| What does diligence need to find? | §20, §26–§27 |
| Startup valuation/dilution? | §28 |
| Dispute/divorce/estate? | §30 |
| Non-profit merger/sale? | §31–§34 |
| Is this charity healthy/effective? | §35–§38 |

### 42.4 Red flags (three = slow down)
- [ ] **Unsupported add-backs or "pro forma" earnings**; **no tax returns/bank statements**
- [ ] **Top customer >20%**; **owner is the business**
- [ ] **Asking price far above comps for size**; a story instead of numbers
- [ ] **Price depends on earnouts/rollover** with unclear metrics
- [ ] **Buyer's financing unproven** (SBA standby-note math doesn't work)
- [ ] **Discount rate ≤10% on a small company**; terminal value >75% of EV
- [ ] **Non-profit:** restricted-fund borrowing; **<2 months of cash**; **>40% from one funder**; **repeat audit findings**; insider transactions without FMV process

---

## §43. Method

**Stable material** (standards of value, approaches, normalization, deal structure, non-profit legal frameworks) reflects established valuation and transaction practice. **Dated material** (§9.3, §28.2, §35, §40) comes from searches on **October 6, 2026**.

**Confidence.**
- **High:** valuation framework; GF Data and BizBuySell figures (reported summaries of primary releases); Giving USA 2026; QSBS and charitable-deduction rules; all arithmetic (computed and tested).
- **Medium:** rates and Fed details (primary news plus secondary pages that disagreed in places); SBA SOP details (advisor summaries); S&P valuation (secondary); non-profit stress data (advisor/survey summaries).
- **Low / unverified (flagged inline):** the 20-year Treasury input; the $10M SBA cumulative limit; startup data for 2026; SaaS multiples (vendor sources); owner-dependency discounts; Single Audit and indirect-rate thresholds; §4958 dollar amounts.

**Source quality.** Many 2026 pages on multiples, SBA rules and "how to sell your business" are **broker or advisor marketing**; they're useful but commercially motivated, sometimes self-contradictory (e.g., multiples quoted as 2.65× or 2.7×; PitchBook vs MergerMarket volumes), and occasionally stale (one rate page still showed pre-hike values). I preferred primary releases (BizBuySell, GF Data via ACG, Giving USA, Kroll, CNBC) and flagged the rest.

**Three deliberate choices.**
1. **Show the error of the naive method first.** The synthetic test shows a median multiple missing EV by **16.4% (90th percentile 36.9%)** and a size-band median by **12.1%**, versus **1.7%** for a regression that recovers the true drivers: the central lesson for private-company pricing. ⚠️ **Real data is noisier and the regression is correctly specified in the simulation: expect 2–3× larger errors in practice.**
2. **Treat structure and tax as part of value.** Present value of structured offers (~87.5% of headline), **$170,000** asset-vs-stock tax difference, and QSBS cliffs change decisions more than a half-turn of multiple.
3. **Treat non-profits as a separate problem, not a "for-profit with no profit."** They have no owners; the key questions are **restrictions, liabilities, liquidity, concentration and mission continuity**: the framework in §31–§38 uses **fair-value and unencumbered net assets, §4958 process, and ratio stress tests** instead of price.
**When this reference is next refreshed, update §40 first** (rates, Kroll inputs, multiples, SBA rules, Giving USA, tax rules), then §9.3, §28.2 and §35.
