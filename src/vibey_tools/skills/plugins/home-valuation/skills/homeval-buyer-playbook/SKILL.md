---
name: homeval-buyer-playbook
description: "Use when buying a house: budgeting from the payment backward (rates, insurance, taxes, DTI, PMI, loan limits), the written buyer-agent agreement you now sign before touring, searching and reading listings and price history, valuing the target and setting an offer ladder (open / target / walk-away), offer terms and contingencies by market regime, appraisal-gap handling, the 30-day due-diligence timeline (inspection, title, insurance, HOA, closing disclosure, wire-fraud protocol), and decision rules for rent vs buy, buy now vs wait, new construction, fixer-uppers and rate buydowns."
---

# Home Valuation and Market Research: The Buyer Playbook

> **Part 4 of 7** of the *Home Valuation and Market Research* reference (plugin `home-valuation`), covering §16–§20. Sibling skills: `homeval-concepts-methods-and-market-structure` (§0–§4), `homeval-market-analysis-and-timing` (§5–§9), `homeval-comps-adjustments-and-avms` (§10–§15), `homeval-seller-playbook` (§21–§25), `homeval-diligence-risk-and-investment` (§26–§30), `homeval-reference` (§31–§35). Code: `scripts/homeval.py` (`piti`, `max_price_from_payment`, `true_monthly_cost`, `dti`, `appraisal_gap_plan`, `rent_vs_buy`).
>
> **Currency:** Procedures are stable; rates, limits and rules are **October 2026** (§4.5 → `homeval-concepts-methods-and-market-structure`). Concession limits and underwriting thresholds change; verify with a lender.

> **⚠️ Scope.** Educational; not lending, legal or investment advice. A pre-approval letter is not a commitment to lend.

> **The three ideas:**
> 1. **⚠️ Price the payment, not the house.** Buying power is set by the *monthly* number your lender and your life can carry. At 7.28% vs 6.01%, the same $2,600 monthly budget buys about **$319,000 vs $355,000** of house (§16).
> 2. **⚠️ Decide three prices before you see the house: open, target and walk-away.** The walk-away price is the lower of your payment ceiling and the top of the valuation range. Never revise it upward *during* a negotiation (§18).
> 3. **⚠️ The contract is the protection.** Contingencies, deadlines and earnest-money rules, not conversations, protect you. Every spoken promise must be in writing (§19).

---

## §16. Define the Decision: Budget, Financing and Total Cost

### 16.1 Build the budget backward (use the toolkit)
```python
import homeval as hv
hv.max_price_from_payment(target_total=2600, down_pct=10, rate_pct=7.28,
                          tax_rate_pct=0.9, insurance_annual=3057, hoa_monthly=0, pmi_rate_pct=0.6)  # → ~$318,700
hv.piti(price=429_100, down_pct=10, rate_pct=7.28, tax_rate_pct=0.9, insurance_annual=3057, pmi_rate_pct=0.6)
hv.true_monthly_cost(piti_total, price, maintenance_pct=1.0, utilities_monthly=250)
```
- **Example (verified):** $429,100 home, 10% down, 7.28%, 0.9% tax, $3,057 insurance, 0.6% PMI → P&I **$2,642** + tax $322 + insurance $255 + PMI $193 = **PITI $3,412/mo**; add 1%/yr maintenance reserve ($358) and utilities ($250) → **all-in ≈ $4,020/mo**. The same house at the Feb 2026 low (6.01%) would have been **$324/mo cheaper** in PITI.
- **Rule:** budget on **all-in cost** (PITI + maintenance reserve + utilities + commute delta + HOA), keep **6 months of reserves** after closing, and avoid sizing a loan to the lender's maximum.

### 16.2 Qualification basics (verify with a lender)
| Item | Typical rule / range | Note |
|---|---|---|
| **Down payment** | Conventional from 3%; FHA 3.5%; VA/USDA 0% (eligibility) | <20% down on conventional → PMI (cancelable at ~80% LTV) |
| **Debt-to-income** | **FHA baseline ~43%** (automated underwriting can allow more); conventional commonly up to ~45–50% with strong compensating factors | Back-end DTI = (housing + other debts) ÷ gross income; toolkit `dti()` |
| **Credit score** | Drives rate and PMI; thresholds at 620/680/740+ | Pull your own reports first; fix errors; avoid new credit before closing |
| **Loan limits (2026)** | Conforming **$832,750** (high-cost ceiling **$1,249,125**); FHA **$541,287–$1,249,125** | Above = jumbo (stricter reserves, different pricing) |
| **PMI** | Roughly 0.3–1.5%/yr of loan, varies with score and LTV | The toolkit uses 0.6% as a placeholder |
| **Rate lock** | 30–60 days typical; extension fees | Ask lock-and-float options; closing-delay risk |

### 16.3 Rate shopping and buydowns
- **Get ≥3 Loan Estimates** (same-day, same loan type, same points) from different lender types (bank, credit union, broker, mortgage company); Freddie Mac's economist advice in 2026 releases was simply that comparison shopping can save thousands over the loan.
- **Buydown math (illustration):** if 1 point (1% of a $386,190 loan = $3,862) cuts the rate 0.25% (7.28% → 7.03%), the payment drops ~$65/mo → **breakeven ≈ 59 months.** If you may move/refinance sooner, don't buy points. **Seller-paid buydowns** are often more efficient than price cuts when rates are high, but they must be disclosed and stay within **seller-concession limits** (commonly tiered by LTV on conventional loans, with separate limits for FHA/VA; ⚠️ verify the current table with your lender) and may affect appraisal treatment.
- **ARMs** and **assumable loans** (FHA/VA) can undercut market rates; assumable loans may require a large cash gap to the seller's equity and lender approval.

### 16.4 The buyer-agent agreement (since Aug 17, 2024)
Before touring (in person or live-virtual) with an MLS-participating agent you will **sign a written agreement stating compensation** (objectively ascertainable; not "whatever the seller offers") and that fees are negotiable. **Negotiate:** flat fee vs percentage; **term** (consider 30–90 days with renewal, not 12 months); **exclusive vs non-exclusive**; **termination for cause/convenience**; protection ("tail") period; what happens when a seller offers compensation (credit against your fee?); dual-agency consent; **scope** (properties/area). Compare 2–3 agents on *local transaction count in your segment, recent comps they'd cite, and how they negotiate repairs and appraisals*, not on friendliness.

---

## §17. Search and Shortlist

### 17.1 Criteria
Write **must-haves (hard), nice-to-haves (priced), dealbreakers (hard)**. Price the nice-to-haves using §11 magnitudes so you can trade them off. Include **commute, flood zone, school zone, noise, HOA rules/rental caps, lot, parking, accessibility, broadband, insurance availability.**

### 17.2 Reading a listing like an analyst
| Signal | Reading |
|---|---|
| **DOM > segment median, repeated cuts** | Seller realism gap; leverage; also a possible defect: ask why |
| **Relisted / new agent** | CDOM matters; sellers who "reset" DOM are hiding history |
| **"As-is", "investor special", "handyman"** | Condition risk; price should reflect cost-to-cure plus contingency (15–20% of rehab budget) |
| **Photos hide a room/exterior/yard** | Hidden problem or poor staging; visit |
| **"Motivated seller"** | Maybe; verify with price history and carrying cost, not language |
| **Price just under a round number** | Band-targeting; negotiate within the band |
| **No price history on a portal** | Possible private-network marketing before listing (§4.2 → `homeval-concepts-methods-and-market-structure`): treat history as incomplete |

### 17.3 Neighborhood and parcel research (30–60 min per finalist)
County **assessor** (tax, assessed value, characteristics, sales history) → **recorder/register of deeds** (liens, easements, deed restrictions) → **GIS/parcel viewer** → **permit history** (open permits, unpermitted additions) → **planning/zoning** (what can be built next door; rezoning; road projects) → **FEMA flood map** and elevation → **utility** (sewer vs septic; water source) → **crime/noise** data and a **site visit at three times** (commute rush, evening, weekend) → **schools** by objective data if relevant.

---

## §18. Value the Target and Build the Offer

### 18.1 The three prices
1. **Value range** from §15 (comps + regression + AVMs + live competition).
2. **Payment ceiling** from §16.1 (the number you can carry with reserves).
3. **Walk-away** = `min(payment ceiling, high end of value range × (1 + overpay tolerance))`. Define "overpay tolerance" (0–3%) *in advance* and what unique features justify it (view, lot, school). **Write it down.**
- **Open** = low end of the defensible range (not an insult: *show the three comps that justify it*).
- **Target** = midpoint of range, adjusted for regime (§9.1).

### 18.2 Offer terms (price is only one lever)
| Lever | Strengthens your offer | Cost/risk to you |
|---|---|---|
| **Price** | Higher | Direct |
| **Earnest money** (commonly ~1–3% of price; varies by state/region) | Larger deposit | At risk if you breach/contingencies lapse |
| **Contingencies** (inspection, appraisal, financing, sale-of-home) | Fewer/shorter | **Each waiver transfers risk to you**; never waive financing unless you can fund |
| **Inspection period** | Shorter | Less time to find defects |
| **Closing date / possession** | Match seller's need; rent-back | Moving flexibility |
| **Appraisal-gap coverage** | "Up to $X above appraisal" | Cash exposure (§18.4) |
| **Financing** | Pre-underwritten, cash, larger down | Time/effort |
| **Escalation clause** | Beats unknown bids | Reveals your max; lenders/appraisers still cap by appraisal |
| **Seller concessions asked** | None | Weaker offer in tight markets, stronger tool in buyer-leaning markets |

⚠️ **Avoid "love letters"/personal narratives** where agents or brokerages advise against them (fair-housing exposure); rely on terms.

### 18.3 Tactics by regime (from §9.1 → `homeval-market-analysis-and-timing`)
- **Hot/seller-leaning:** clean financing, tight timelines, price near ceiling *if inside your walk-away*; skip home-sale contingency; offer a rent-back; escalate within limits.
- **Balanced:** negotiate on repairs and credits; ask for rate buydown or closing-cost help in lieu of price cuts; keep inspection and appraisal contingencies.
- **Buyer-leaning (the 2026 national picture):** open below list with comps, request **closing-cost credits or a seller-paid buydown**, extend inspection to 10–14 days, include a **price-reduction-after-inspection clause**, and target **stale listings** (CDOM above median, ≥2 cuts). Redfin's own agents in Sept 2026 described buyers as able to "afford to be picky" and sellers needing to price correctly from the start.
- **Always:** *name the evidence*. "Three closed comps within 0.5 mile at $X–$Y after adjustments; the active listing at $Z is larger and cheaper per square foot."

### 18.4 The appraisal gap
The lender funds the **lower of price or appraised value**. If appraisal < price:
| Option | Use when |
|---|---|
| **Ask for reconsideration of value** with 2–4 better comps and a list of omitted features | Evidence supports a higher value (do it quickly, via the lender) |
| **Renegotiate price** to the appraisal (or split the gap) | Appraisal contingency intact; market supports it |
| **Cover gap in cash** | Only if inside your walk-away and reserves remain |
| **Switch lender/appraisal** | Rarely allowed; time-consuming |
| **Walk** | Contingency intact and price > your walk-away |
`appraisal_gap_plan(offer, appraised, down_payment, cash_reserve)` gives the gap and which options apply.

---

## §19. Under Contract: The Due-Diligence Timeline

| Day | Task | Notes |
|---|---|---|
| **0** | Earnest money deposited; contract signed by all parties; lender gets contract | Verify the escrow/attorney by phone number from a trusted source |
| **0–3** | **Loan Estimate** within 3 business days of application; lock rate; order inspection; send HOA docs request | Dates in the contract are legal deadlines |
| **1–7** | **General inspection**; add-ons as warranted: **sewer scope, radon, WDI/termite, roof, foundation/structural engineer, mold, electrical panel, chimney, septic, well/water test** | Ask for old-wiring, old-plumbing and system-age red flags (§26) |
| **3–10** | **Homeowners insurance quotes** (bind a policy to the property) and **flood** determination; check CLUE/claims history, wind/hail deductibles | **Do this before contingencies lapse**; premium and availability change value (§27) |
| **5–14** | **Repair negotiation:** request (a) repairs by licensed contractors with receipts, (b) **credit at closing** (often easier for the seller and lender-compatible), or (c) price reduction | Prioritise safety/structural/water over cosmetics |
| **7–21** | **Appraisal**; **title commitment** and survey; HOA financials (reserves, special assessments, litigation, rental caps, insurance) | Lender cannot proceed without clear title |
| **21–28** | Clear **underwriting conditions**; finalize insurance | Don't change jobs, open credit or move money without telling your lender |
| **≥3 business days before closing** | **Closing Disclosure** received; compare to Loan Estimate; verify cash-to-close | Federal timing rule; changes in APR/product/prepayment penalty can re-start the clock |
| **24–48 hrs before** | **Final walkthrough** | Confirm repairs, systems working, no new damage; document |
| **Closing** | Wire funds; sign; record | **Wire-fraud protocol:** *call* the title/escrow office at a number you looked up independently to confirm wiring instructions; never act on emailed changes |

**Deal-breaker triggers (stop and renegotiate or walk):** foundation or structural movement, active water intrusion/mold, polybutylene/Federal Pacific/aluminum branch wiring/knob-and-tube without remedy, failing septic/sewer line, roof near end of life in an area where insurers decline or surcharge, unpermitted work that affects value/insurance, flood or fire designation you cannot afford to insure, HOA special assessments or reserves that signal failure, title defects.

---

## §20. Decision Rules for Common Buyer Situations

### 20.1 Rent vs buy (opportunity-cost aware)
`hv.rent_vs_buy(price, down_pct, rate_pct, tax_rate_pct, insurance_annual, maintenance_pct, monthly_rent, years, appreciation_pct, rent_growth_pct, invest_return_pct)`.
**Verified illustration:** $429,100 home, 10% down, 7.28%, taxes 0.9%, insurance $3,057, maintenance 1%, rent $2,400 (rent/price ≈ 0.56%/mo), rent growth 3%, investment return 6%:
| Years | Appreciation | Buy net worth | Rent net worth | Winner |
|---|---|---|---|---|
| 3 | 3% | $57,196 | $109,866 | Rent |
| 7 | 3% | $132,012 | $183,971 | Rent |
| 7 | 5% | $201,976 | $183,971 | **Buy** |
| 15 | 3% | $326,781 | $333,542 | ≈ even |
At these inputs the **break-even is a ~15-year horizon at 3% appreciation, or ~4.5–5% annual appreciation over 7 years.** ⚠️ **Everything depends on your rent-to-price ratio:** at higher ratios (rent ≥ 0.8% of price) buying wins sooner. The model ignores tax deductions (itemizing), tax on investment gains, and non-financial value (stability, control). Run *your* numbers; do not repeat a headline.

### 20.2 Buy now or wait?
- **Waiting wins if:** you can't carry the payment with reserves; you may move in <5 years (transaction costs ~6–10% round trip); your market is *falling* (regime §9.1) and you're not forced to move.
- **Buying now wins if:** you will stay 8+ years; you have buyer's-market leverage (credits, buydown, stale listings); renting costs are rising; you can refinance later if rates fall *and* can survive the current payment.
- **Never** buy because "rates will fall" or "prices will surge"; buy because the all-in cost and the house make sense at today's rate.

### 20.3 New construction
Builder incentives (buydowns, closing credits) are often stronger than resale-seller concessions, **but** (a) the incentive may be built into the price; (b) you still need an **independent inspection** (pre-drywall and final); (c) appraisals can come in below price if the builder's incentives aren't supported by comps; (d) read the warranty and what the builder's lender requires.

### 20.4 Fixer-uppers
Underwrite **price + rehab × (1.15–1.25 contingency) + carrying costs + permits** vs *after-repair value* (§15; use renovated comps). Renovation loans (e.g., FHA 203(k), Fannie Mae HomeStyle) fund purchase + rehab. Get **contractor bids before removing contingencies.** Verify permits and that the finished product is saleable.

### 20.5 Relocating or buying remotely
Hire **local** representation and inspection; insist on a **live video walkthrough** plus a trusted local to attend; verify flood, noise, commute and neighborhood by independent data (§17.3); keep the inspection contingency.

### 20.6 First-time buyers
Research state **housing finance agency** programs (down-payment assistance, credit certificates) and their income/price caps; evaluate FHA vs conventional-3%-down total cost (PMI/MIP differences); keep reserves.

---

## §20A. Buyer Checklists

**Before you search:** [ ] pre-approval from 2+ lenders [ ] three Loan Estimates [ ] all-in monthly cost and reserves [ ] must-haves/dealbreakers [ ] agent agreement terms negotiated.
**Before you offer:** [ ] value range (§15) [ ] walk-away price written [ ] insurance + flood quote requested [ ] comps for negotiating [ ] contingencies chosen.
**Under contract:** [ ] inspections scheduled [ ] insurance bound [ ] HOA docs [ ] title/survey [ ] appraisal handled [ ] repair/credit settled in writing [ ] Closing Disclosure reviewed [ ] wire verified by phone [ ] walkthrough.
