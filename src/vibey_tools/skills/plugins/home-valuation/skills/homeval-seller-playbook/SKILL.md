---
name: homeval-seller-playbook
description: "Use when selling a house: the net-proceeds sheet and cost of waiting, the lock-in effect and sell-then-buy sequencing, the Section 121 home-sale exclusion, three-price pricing strategy by market regime (value / list / floor), listing-agent interviews and listing-agreement terms, prep and renovation ROI (Cost vs Value 2025 and why its numbers need skepticism), marketing exposure and private-listing trade-offs, buyer-agent compensation and concessions, evaluating offers on net not headline, handling low appraisals and inspection requests, and FSBO / cash-offer / inherited / problem-property situations."
---

# Home Valuation and Market Research: The Seller Playbook

> **Part 5 of 7** of the *Home Valuation and Market Research* reference (plugin `home-valuation`), covering §21–§25. Sibling skills: `homeval-concepts-methods-and-market-structure` (§0–§4), `homeval-market-analysis-and-timing` (§5–§9), `homeval-comps-adjustments-and-avms` (§10–§15), `homeval-buyer-playbook` (§16–§20), `homeval-diligence-risk-and-investment` (§26–§30), `homeval-reference` (§31–§35). Code: `scripts/homeval.py` (`seller_net`, `carrying_cost_of_waiting`, `home_sale_gain`, `market_stats`, `reconcile`).
>
> **Currency:** Procedures stable; the §23 renovation ROI figures are from the **2025 Cost vs. Value report (38th edition)**, the latest I could verify; a newer edition is typically published in the fall. Tax rules are US federal and **unchanged for 2026** as far as I could verify (§21.4); state rules vary.

> **⚠️ Scope.** Educational; not legal, tax or brokerage advice. Fees and practices are negotiable and vary by state and brokerage. Tax outcomes depend on facts you must review with a CPA.

> **The three ideas:**
> 1. **⚠️ Net proceeds, not list price, is the outcome.** A $429,100 sale with 1.5% concessions nets about **$180,505**; the same house at $420,000 with no concessions nets **$178,360**: a $9,100 price difference was worth only ~$2,100 after concessions (§21.1). Compare offers on *net, risk and certainty.*
> 2. **⚠️ In a cooling market the first two weeks decide the outcome.** Price to where the best recent comps *and* today's competing listings support on day 1. A price cut later is read by buyers as weakness and is visible on every portal (§22).
> 3. **⚠️ Prep to remove objections, not to express taste.** Spend on defects, cleanliness, light, curb appeal and photographs; avoid large discretionary remodels (§23).

---

## §21. Decide to Sell: Net, Timing and Taxes

### 21.1 The net-proceeds sheet (build it before you call an agent)
```python
import homeval as hv
hv.seller_net(price=429_100, mortgage_payoff=210_000, listing_comm_pct=2.5, buyer_comm_pct=2.5,
              seller_concessions_pct=1.5, transfer_tax_pct=0.2, title_escrow_pct=0.5,
              prep_costs=4_500, repairs_credit=2_000, prorated_taxes_hoa=1_200)
```
**Verified output:** commissions $21,455; concessions $6,437; transfer tax $858; title/escrow $2,146; prep $4,500; repairs credit $2,000; prorations $1,200 → **total costs $38,595 (9.0% of price)** → **net $180,505** after a $210,000 payoff.

| Scenario (payoff $210k, same cost assumptions) | List/Sale | Concessions | Costs % | **Net** |
|---|---|---|---|---|
| A | $440,000 | 0% | 7.5% | **$197,220** |
| B | $429,100 | 1.5% | 9.0% | $180,505 |
| C | $420,000 | 0% | 7.5% | $178,360 |
| D | $415,000 | 3.0% | 10.6% | $161,195 |
⚠️ **Lessons:** concessions are real money; a lower-priced clean offer can beat a higher-priced offer with concessions; commission treatment (§24.2) swings costs by a point or more. Typical total selling costs run roughly **6–10% of price** (⚠️ commission ranges are practitioner-reported; get quotes).

### 21.2 The cost of waiting
`carrying_cost_of_waiting(monthly_piti, monthly_utilities, months, price, monthly_drift_pct)`:
- Carry $2,900 + $300 utilities × 3 months = **$9,600**.
- Expected price change over 3 months at **−0.2%/mo = −$2,569** (net −$12,169); at **+0.2%/mo = +$2,580** (net −$7,020).
- **Waiting is rational only if the expected monthly price gain exceeds carry ÷ price (~0.75%/mo here).** In a flat or falling market it is rarely worth it, *unless* you can rent the house out profitably or you're not carrying the payment.

### 21.3 The lock-in effect and replacement cost
Many owners hold sub-4% mortgages. **P&I per $100k at 3.5% is $449 vs $684 at 7.28%.** Selling means trading a $1,347 payment (a $300k 3.5% loan) for ~$1,700 on a $248,595 loan *even after* moving to an equal-priced home with $180,505 equity as the down payment (the example above). That cost is your real "price of moving." **Decide with replacement cost, not just sale price.** Sequencing options:
| Sequence | Pros | Cons |
|---|---|---|
| **Sell, then buy (rent in between)** | Clean; known equity; stronger buyer on the next purchase | Double move; rent; market risk on the buy |
| **Buy, then sell (bridge/HELOC)** | Move once; shop calmly | Two payments; qualification; risk of selling lower |
| **Contingent purchase (sale-of-home contingency)** | Limits risk | Weak offers in competitive markets |
| **Sell with rent-back/late closing** | Time to find the next home | Buyer must accept; insurance/occupancy terms |

### 21.4 Taxes (US federal; educational; consult a CPA)
- **Section 121 exclusion:** up to **$250,000 (single) / $500,000 (married filing jointly)** of gain on your **principal residence**, if you **owned and used it as your main home for 2 of the 5 years** before sale and haven't used the exclusion on another sale in the prior 2 years. **Thresholds are not indexed to inflation** and have been unchanged since 1997. I found no 2026 enactment changing them (the "No Tax on Home Sales Act" and similar bills have been proposed; ⚠️ verify current law).
- **Gain** = (sale price − selling costs) − **adjusted basis** (purchase price + qualifying closing costs + capital improvements). **Keep receipts for improvements** (additions, roof, HVAC, kitchens) to raise basis. `home_sale_gain()` estimates the taxable gain above the exclusion.
- **Partial exclusion** (job change, health, unforeseen circumstances): prorated by months/24 (e.g., 15 months → 15/24 × $250,000 = $156,250).
- **Complications:** depreciation recapture if part of the home was rented or used for business; divorce/death rules; **state taxes** (some states don't conform; e.g., ⚠️ one source says PA doesn't recognize §121 treatment: verify); **inherited property gets a stepped-up basis** to fair market value at the date of death (very different gain, valuation date matters: get an appraisal as of that date).

---

## §22. Pricing Strategy

### 22.1 Three prices
1. **Value range** (§15) and the **competition ceiling** (best 3 active/pending homes that rival yours).
2. **List price**: where you start, set by regime (§9.1 → `homeval-market-analysis-and-timing`).
3. **Floor** (walk-away net): the lowest net proceeds you accept, from §21.1 and your replacement plan. **Set before listing.**

### 22.2 Pricing by regime
| Regime | List price rule | Why |
|---|---|---|
| **Hot** | At or slightly below comps to *generate multiple offers*; set an offer deadline | Competition raises price; low list → more viewers |
| **Balanced** | At the **reconciled value**; avoid the "room to negotiate" markup | Buyers anchor on comps; overpricing wastes the new-listing spike |
| **Buyer-leaning (2026 national)** | **At or modestly below the latest closed comps** (which already lag), *or* at comps with a funded concession/buydown | Redfin agents in Sept 2026: buyers "can afford to be picky", pricing correctly from the start is critical; 21.1% of sellers were cutting |
| **Falling** | Price to the *pending* prices, not closed prices; consider renting | Closings lag the market |

### 22.3 Decision rules from early market feedback (heuristics, not laws)
| Observation (first 10–14 days) | Likely cause | Action |
|---|---|---|
| Few online views | Price band, photos, headline, wrong portal exposure | Fix photos/description; test price band edge |
| Views OK, few showings | **Price too high for the features** or poor first impression | Re-check comps incl. active competition; adjust price |
| Showings OK, no offers | **Condition/price/odor/layout** vs alternatives | Collect feedback; fix cheap items; adjust price or add concession |
| Offers but low | Market's price is lower | Counter with evidence; consider a price reset |
| Multiple offers | Priced to demand | Run a clear process (§24) |
**Price changes:** cut **decisively** (a meaningful step that changes search bands), not by token 1%. Avoid delist/relist games; they reset visible DOM in some systems but portals often keep price history; buyers' agents see through them.

### 22.4 Choosing the listing agent (interview 2–3)
Ask for **their pricing recommendation with the comps they used** (not just a number: beware **inflated "buy the listing" prices**), their **marketing plan** (photos, 3D/floor plan, exposure and *when*), **recent sales in your segment** (count, list-to-sale ratio, DOM, share requiring price cuts), **negotiation record on appraisals and repairs**, communication plan, and **fee quote** (listing fee; buyer-side compensation recommendation; what's included).
**Listing agreement terms to negotiate:** term (e.g., 90 days not 6–12 months), **cancellation right**, **protection period**, **MLS entry timing** (no gated private marketing without your informed consent), concession policy, **dual agency**, referral fees, who pays for photography/staging.
**Evidence worth knowing:** a well-known study (Levitt & Syverson, ~2005 Chicago-area data; ⚠️ old, one region) found agents sold *their own* homes for ~3.7% more and held out longer than clients' homes; the point is **incentives differ**: a 1% change in price is worth far more to you than to a percentage-paid agent. Align by contract (e.g., tiered fee).

---

## §23. Prep and Renovation ROI

### 23.1 Spend order (highest → lowest expected return)
1) **Fix defects the buyer will find** (roof leaks, drainage, safety items, HVAC failure, electrical) or **price/credit them**; 2) **clean, declutter, depersonalize, deep-clean, neutral paint and lighting**; 3) **curb appeal and entry** (door, garage door, landscaping, lighting, power-wash); 4) **professional photos/video/floor plan**; 5) **minor kitchen/bath refresh** (hardware, paint, fixtures, counters if dated); 6) *avoid* major kitchen/bath/addition projects, pools and outdoor rooms unless your comps show buyers pay for them locally.

### 23.2 Cost vs. Value: use with skepticism
**2025 Cost vs. Value (38th edition, national averages; Zonda/Remodeling):**
| Project | Job cost | Value at sale (survey) | Cost recouped |
|---|---|---|---|
| Garage-door replacement | $4,672 | $12,507 | **267.7%** |
| Steel entry door | $2,435 | $5,270 | **216.4%** |
| Manufactured stone veneer | $11,702 | $24,328 | **207.9%** |
| Minor kitchen remodel | $28,458 | $32,141 | **112.9%** |
| Vinyl siding | $17,950 | $17,313 | 96.5% |
| Backup generator | $13,534 | $12,902 | 95.3% |
| Wood deck | $18,263 | $17,323 | 94.9% |
| Composite deck | $25,096 | $22,199 | 88.5% |
| Fiberglass grand entrance | $11,754 | ~$9,960 | ~84.7% |
| Asphalt roof (2025, secondary source) | – | – | ~68% (2024: 56.9%) |
| Major kitchen remodel (older data) | – | – | ~51% |

⚠️ **Why to doubt >100% figures:** the "value at sale" is **estimated by surveyed real-estate professionals**, not measured from transactions; the *same report* showed ~93–95% recoup for a garage door in 2020–2022 and ~194% in 2024 before 268% in 2025. Treat as **"which projects buyers respond to," not "I'll make 268%."** Also: (1) the list price you can *ask* is capped by comps; (2) many projects' value is **avoiding objections**, not adding dollars; (3) regional variation is large. **Verify with local agents' sold-comp evidence and appraisers.**

### 23.3 Pre-listing inspection / appraisal
- **Pre-inspection:** finds issues before buyers do, lets you fix or price them, reduces renegotiation risk; cost ~a few hundred dollars. If you do it, **disclose findings per state law**.
- **Pre-listing appraisal:** useful for unusual homes or to anchor against an agent's inflated price; not binding on buyers' lenders.
- **Staging:** evidence on staging is mixed and often agent-reported; vacant homes benefit from at least partial staging or virtual staging (**disclose** virtual staging and AI edits; don't misrepresent condition).

### 23.4 Permits and disclosure
Unpermitted additions can **cut value (appraisers exclude non-permitted GLA), complicate financing, and expose you to liability**. Pull permit history; **cure or disclose**. Disclose known material defects per your state's rules; "as-is" doesn't excuse concealment.

---

## §24. Marketing, Offers and Closing

### 24.1 Exposure
- **Enter the MLS** (or equivalent) so the property reaches all agents and portals; **Clear Cooperation** requires MLS entry within one business day of public marketing (§4.2 → `homeval-concepts-methods-and-market-structure`). A "private exclusive" period limits buyer exposure; if you consider it, get in writing **what it costs you in reach, for how long and what you get in return.**
- **Quality of listing assets drives views:** first photo, professional photography, floor plan, accurate description, specific selling points (energy bills, roof/HVAC dates, recent upgrades with receipts), a pre-listing document package (disclosures, HOA documents, survey, permits, inspection summary).

### 24.2 Compensation to buyers' agents and buyers
Since Aug 2024, compensation offers can't be shown on the MLS, and **sellers may choose** to offer compensation or concessions to buyers or their agents off-MLS. Practice varies by market. Decide using data: **what competing homes offer**, how many buyers in your tier use agents, and the net effect (§21.1). Alternatives: *offer a concession toward closing costs/rate buydown (usable by buyer, not conditioned on agent)*, or *offer none and price accordingly*. Document the choice in the listing agreement.

### 24.3 Evaluating offers: score on net, certainty and speed
| Factor | What to compare |
|---|---|
| **Net proceeds** (after concessions, credits, fees) | The toolkit sheet for each offer |
| **Financing strength** | Cash > conventional with strong pre-underwriting > FHA/VA (appraisal & repair conditions) > contingent on sale |
| **Contingencies** | Inspection length; appraisal; financing; home-sale |
| **Appraisal-gap coverage** | Guaranteed vs hope |
| **Earnest money** | Amount and when it goes hard |
| **Timeline/possession** | Match to your next move; rent-back |
| **Buyer's agent/lender record** | Failed deals are costly |
| **Backup position** | Accept a backup offer |
**Multiple offers:** set a deadline, request "highest and best" by a time, ask for **proof of funds/pre-approval and lender contact**, evaluate net not headline; treat **escalation clauses** carefully (require verification of the competing offer). Fair housing: process must be neutral and documented.

### 24.4 After acceptance
- **Inspection response:** triage by safety/structure/water/cosmetic; offer **credit at closing** for non-critical items (fewer contractor delays); fix critical items with receipts. Counter, don't capitulate: tie requests to the inspector's report and comps.
- **Low appraisal:** (see §18.4 → `homeval-buyer-playbook`): evidence-based reconsideration; renegotiate within your floor; compare to the next backup offer.
- **Closing:** confirm payoff statement, HOA transfer docs, utilities, keys/possession, **wire-fraud protocol** (never trust emailed instructions; verify by phone), final walkthrough readiness, 1099-S/tax reporting, **keep the closing statement for basis/tax records.**

---

## §25. Special Seller Situations

| Situation | Notes |
|---|---|
| **FSBO** | You still need a valuation (§15), a state-compliant contract and disclosures, MLS-equivalent exposure (flat-fee MLS), and a plan for **buyer-agent requests** (buyers are now asked to sign agreements; some will want compensation). Savings can be wiped by a 3–5% underpricing or a bad contract: consider hourly agent/attorney review |
| **Cash/instant ("iBuyer"/investor) offers** | Compare **net** to a conventional sale: service fees, repair deductions, concessions; speed/certainty have value; ask for the offer as a written net sheet |
| **Inherited property** | Obtain a **date-of-death appraisal** (stepped-up basis); address probate authority, title, insurance on vacant homes, and carrying costs; sell vs rent decision (§28 → `homeval-diligence-risk-and-investment`) |
| **Divorce** | One spouse keeping the house may lose the $500k joint exclusion (single $250k); document ownership/use timelines; use an independent appraisal agreed by both |
| **Tenant-occupied** | State rules on notice/showings; buyer pool shrinks to investors unless vacated; verify leases and security deposits |
| **Problem property** (foundation, flood history, septic, unpermitted work, mold, stigma) | **Disclose fully**; get repair estimates/engineer letters; price the *cost to cure* plus risk margin; target buyers with contractor access or cash; expect lender and insurer hurdles |
| **Buyer-leaning market, can't wait** | Price to the pending/competition ceiling; fund a **rate buydown** (often more attractive to buyers than an equal price cut at high rates); remove friction (flexible closing, pre-inspection) |
| **Can wait** | Rent it out only if the §28 income math works at current rates; otherwise holding costs and taxes can exceed price drift |

---

## §25A. Seller Checklists

**60–90 days before:** [ ] value range (§15) [ ] net sheet [ ] replacement plan [ ] tax advice [ ] 2–3 agent interviews with comps [ ] repair/cleaning plan [ ] gather improvement receipts/permits.
**Listing week:** [ ] photos/floor plan [ ] disclosure package [ ] showings access plan [ ] price + floor written [ ] exposure plan confirmed [ ] concession strategy.
**Weeks 1–2:** [ ] daily views/showings/feedback log [ ] adjust per §22.3.
**Under contract:** [ ] earnest money received [ ] inspection response [ ] appraisal [ ] title/payoff [ ] walkthrough [ ] wire verification [ ] closing statement saved.
