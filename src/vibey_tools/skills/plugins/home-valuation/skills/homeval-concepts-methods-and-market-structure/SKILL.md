---
name: homeval-concepts-methods-and-market-structure
description: "Use first for any house-value question: what 'value' means (market value vs price vs assessed vs appraised vs insurable), the three approaches to value and when each applies, how appraisals, CMAs, BPOs, AVMs and tax assessments differ in accuracy and legal weight, the UAD 3.6 appraisal change (mandatory Nov 2, 2026), and the rules of the US market (NAR settlement, written buyer agreements, Clear Cooperation and the private-listing fight, attorney vs title-company states, disclosure regimes, fair housing). Includes the router for the whole home valuation and market research reference."
---

# Home Valuation and Market Research: Concepts, Methods and Market Structure

> **Part 1 of 7** of the *Home Valuation and Market Research (buying and selling a house)* reference (plugin `home-valuation`), covering §0–§4. Sibling skills: `homeval-market-analysis-and-timing` (§5–§9), `homeval-comps-adjustments-and-avms` (§10–§15), `homeval-buyer-playbook` (§16–§20), `homeval-seller-playbook` (§21–§25), `homeval-diligence-risk-and-investment` (§26–§30), `homeval-reference` (§31–§35). Section numbers are shared across the set; §N → `skill` points into a sibling. Companion code: `scripts/homeval.py` (tested; see §15 → `homeval-comps-adjustments-and-avms`).
>
> **Currency:** Valuation theory is stable (decades). Market statistics, mortgage rates, loan limits and industry rules are dated **October 2026** and flagged where they move; see §32 → `homeval-reference` for what changed.

> **⚠️ Scope.** This is an explanatory and procedural reference. **It is not appraisal, legal, tax, lending or investment advice**, and a self-run valuation is not a USPAP-compliant appraisal. Rules differ by state and change; anything with real money attached deserves a licensed local professional (appraiser, real-estate attorney, CPA, lender). Where a figure comes from a single or commercially motivated source, it is marked.

> **The three ideas that organize everything here:**
> 1. **⚠️ Price is a fact; value is an opinion about the most probable price.** A sale price happened. A value is a forecast of what would happen under stated conditions. Never mix the two, and never present a value without a date, a purpose and an error band.
> 2. **⚠️ Every estimate has an error bar, and the bar is wide.** Zillow's own published median error is ~1.8% for homes already on the market but ~7.2% for homes that are not (refresh of Aug 8, 2026). On a $430,000 house, 7.2% is ±$31,000, and that is the *median*; half of estimates are worse (§14 → `homeval-comps-adjustments-and-avms`).
> 3. **⚠️ Triangulate independent methods.** Comps, a regression, the market's live competition (active/pending listings) and, for income property, an income approach fail in *different* ways. When they agree, confidence is earned; when they disagree, the disagreement is the finding.

---

## §0. How to Use This Reference (router)

| You are… | Read first | Then |
|---|---|---|
| Unsure what "value" means / who to trust | §1–§3 (this skill) | §14 → `homeval-comps-adjustments-and-avms` |
| Researching a market (city, zip, tier) | §5–§9 → `homeval-market-analysis-and-timing` | §32 → `homeval-reference` for the Oct 2026 snapshot |
| Valuing one specific house | §10–§15 → `homeval-comps-adjustments-and-avms` | run `scripts/homeval.py` |
| Buying | §16–§20 → `homeval-buyer-playbook` | §26–§27 → `homeval-diligence-risk-and-investment` |
| Selling | §21–§25 → `homeval-seller-playbook` | §26 → `homeval-diligence-risk-and-investment` |
| Evaluating a rental / flip | §28 → `homeval-diligence-risk-and-investment` | §10–§13 for the resale exit value |
| Checking a claim or number | §31–§35 → `homeval-reference` | |

**The immediate-use loop (any property, any side):** 1) define purpose and date (§1) → 2) read the market regime (§5–§9) → 3) pull and filter comps (§10) → 4) adjust and reconcile (§11–§12, §15) → 5) cross-check with a regression and AVMs (§13–§14) → 6) stress-test with live competition and carrying costs (§17–§18, §22) → 7) state value as a range with a confidence statement (§15.4).

---

## §1. What "Value" Means

| Concept | Definition | Who produces it | Typical gap from market value |
|---|---|---|---|
| **Market value** | Most probable price in a competitive, open market: knowledgeable, unpressured parties, reasonable exposure time, cash or cash-equivalent financing | Appraiser (formal) or you (informal) | — |
| **List price** | What the seller asks | Seller + listing agent | Strategy, not evidence. Can be below or above market |
| **Sale (contract) price** | What a buyer and seller actually agreed | Transaction | May include concessions that make it differ from a "cash-equivalent" price |
| **Appraised value** | Appraiser's opinion for a specific client/purpose, lender-ordered usually | Licensed appraiser | Can come in under contract price ("appraisal gap", §18) |
| **Assessed value** | County's value for property tax, often on a stale schedule, with caps/ratios | Assessor | Frequently well below market; in some states resets on sale |
| **Insurable / replacement cost** | Cost to rebuild, excluding land | Insurer / estimator | Unrelated to market value; can exceed it in low-priced areas |
| **Investment value** | Value to a particular investor given their financing, tax and return needs | Investor | Subjective by design |
| **Liquidation / forced-sale value** | Price under compressed time | Auction/REO | Below market value |

⚠️ **GOTCHAS**
- **Assessed ≠ market.** Never use the tax roll as "the value," but do use it for *relative* comparisons and to see what the tax bill will be after reassessment.
- **Replacement cost ≠ market value.** The cost approach (§2) ties them only for new construction.
- **A price needs its terms.** A $450,000 sale with 4% seller concessions is not the same evidence as $450,000 cash with none. Adjust for financing and concessions before using a sale (§11).
- **"Worth" depends on the buyer pool.** Value is set by the marginal buyer: the next-best qualified buyer the house must compete for, whose payment budget is rate-dependent (§7 → `homeval-market-analysis-and-timing`).

---

## §2. The Three Approaches (and a Fourth Lens)

| Approach | Core logic | Best for | Weakness |
|---|---|---|---|
| **Sales comparison** | Similar homes recently sold, adjusted to the subject | Single-family, condos, townhomes with active markets | Needs good comps; adjustments are judgment; thin markets |
| **Cost** | Land value + replacement cost new − depreciation | New construction, unique/special-purpose, insurance, rural | Depreciation is hard to measure; buyers don't pay cost |
| **Income** | Net operating income ÷ cap rate (or DCF) | Rentals, multifamily, commercial | Rents, expenses and cap rate are all estimates (§28 → `homeval-diligence-risk-and-investment`) |
| **Fourth lens: substitution / live competition** | What the buyer could get instead right now (active & pending listings) | Pricing and offers in a *moving* market | Listings are asks, not outcomes; use as a ceiling and a trend signal |

**Reconciliation, not averaging.** Appraisers weight the approach and the individual comps by reliability: the comp needing the least adjustment counts most (the toolkit's `reconcile()` does this). **For owner-occupied single-family homes, sales comparison carries almost all the weight; the cost and income approaches are cross-checks.**

**Highest and best use** (land, teardowns, large lots): the legally permissible, physically possible, financially feasible and maximally productive use. A house worth $300k on a lot worth $450k is a land sale (check zoning first).

---

## §3. Who Produces Value Opinions (and What Each Is Good For)

| Product | Made by | Basis | Accuracy (indicative) | Legal weight | Best use |
|---|---|---|---|---|---|
| **Full appraisal** | State-licensed/certified appraiser (USPAP) | Inspection + comps + reconciliation | Strongest available single opinion; still an opinion | Lender-grade | Financing; disputes; estates; divorce |
| **Desktop / hybrid / drive-by** | Appraiser w/ limited inspection or a data collector | Reduced scope | Good where data is rich | Varies by purpose | Refi, HELOC |
| **CMA** (comparative market analysis) | Real-estate agent | Comps + agent judgment | Depends on the agent; no licensing standard like USPAP | Not an appraisal; cannot be used for most lending | Pricing a listing; offer strategy |
| **BPO** (broker price opinion) | Broker/agent for lender/servicer | Quick comps + exterior | Rough | Lender internal | Defaults/REO |
| **AVM** (automated valuation model) | Zillow, Redfin, Cotality, HouseCanary, Fannie/Freddie internal models, etc. | Statistical model on public + MLS data | ~2% median on-market; ~7% median off-market (§14) | Screening/lending support only | First look, sanity check, portfolio |
| **Tax assessment** | County assessor | Mass appraisal | Lags; ratio-based | Tax only | Taxes; relative values |
| **Your own comps analysis** | You | §10–§15 | Comparable to a CMA if done carefully | None | Decisions; negotiation |

**Appraisal facts that matter for buyers and sellers**
- **The lender orders the appraisal** (via an AMC) and you generally cannot pick the appraiser; you can *commission a private appraisal* but a lender won't rely on it.
- **UAD 3.6 / the new URAR:** a dynamic redesigned appraisal report replaces the legacy forms (1004, 1073, 1025, 2055, 1075 and variants) for loans sold to Fannie Mae or Freddie Mac. **Mandatory for new reports first submitted to the UCDP on or after November 2, 2026**; the determining date is *UCDP submission*, not order or effective date. Revisions to UAD 2.6 reports may continue through **May 3, 2027**. ⚠️ The new format changes *reporting*, not how value is estimated; expect more structured data about condition, quality, view and ADU/functional elements, and some turnaround friction during the transition. Sources: Freddie Mac UAD FAQ, Fannie Mae, industry trade groups.
- **Appraisal waivers / "value acceptance"** let some lower-risk loans skip an appraisal; reports in 2025–26 describe GSEs as more conservative with them. Don't plan around a waiver.
- **A low appraisal is information, not a verdict** (§18, §24 for tactics). The lender lends on the *lower* of price or appraised value.
- **Appraiser independence:** neither agent, buyer nor seller may pressure an appraiser to hit a number. Providing *relevant facts* (a list of upgrades with receipts, permits, three better comps) through the proper channel is allowed and normal.

---

## §4. Market Structure and the Rules of the Game (US, Oct 2026)

### 4.1 Agents, commissions and the NAR settlement
- **What changed (effective Aug 17, 2024):** offers of buyer-agent compensation **cannot be displayed on NAR-affiliated MLSs**; agents working with a buyer must have a **written buyer-representation agreement before touring a home** (including live virtual tours), stating compensation in an objectively ascertainable amount (not "whatever the seller offers"), with a conspicuous statement that fees are **negotiable and not set by law**.
- **What did not change:** sellers can still *choose* to offer compensation or concessions to buyers or their agents, but the offer is made **outside the MLS** (listing remarks cannot carry it) and the buyer's agreement governs what the buyer owes.
- **Practical effect:** listing-side fees commonly reported at roughly 2–3% and buyer-side negotiated; (⚠️ these ranges come largely from practitioner and brokerage sources; treat as indicative and **ask for written fee quotes**). All fees are negotiable.
- **Status of litigation:** reports in 2026 describe continued post-settlement litigation, including a proposed $52.25M buyer-claims settlement fund (announced Apr 10, 2026) and an appellate affirmation dated Aug 19, 2026 (⚠️ single practitioner source in my research; verify at the court docket before relying on it).

### 4.2 Private listings, Clear Cooperation and portals
- **Clear Cooperation Policy (CCP):** a listing publicly marketed must be entered in the MLS within **one business day**. It remains in NAR's 2026 MLS handbook.
- **Zillow Listing Access Standards (LAS):** adopted April 2025; a federal court denied Compass's request to block them on **Feb 6, 2026**; Zillow **rewrote the standards on Mar 17, 2026** to emphasize *broad public access* rather than a fixed deadline; **Compass dismissed its suit Mar 18, 2026**; Zillow then sued Compass and MRED (Chicago MLS) on **May 12, 2026**; a Sept 2026 ruling sent the matter back to arbitration. ⚠️ **Live dispute; details will change.**
- **Why it matters to you:** a home marketed in a private network may reach fewer buyers. **Sellers:** ask exactly where and when your home will be visible and what that costs you in competition. **Buyers:** private/"coming soon" inventory exists; ask your agent what is available before it hits portals, and treat missing price history as missing evidence.

### 4.3 Who closes the deal
- **Attorney states** vs **title/escrow-company states:** state law and custom decide who prepares documents and closes. ⚠️ Several southeastern and northeastern states customarily require or use real-estate attorneys; **check your state's rule before choosing representation.** In attorney states, ask who drafts the contract and when counsel is involved (before you sign the offer, ideally).
- **Disclosure regimes:** some states mandate a seller property-condition disclosure form; some are largely *caveat emptor* with limited statutory disclosure (often with exceptions for known latent defects); many have specific disclosures (lead paint pre-1978 is federal; flood, mold, radon, Megan's Law registry and others vary). **A "no representation" or "as-is" form does not erase fraud or concealment liability.**
- **Dual agency / designated agency / transaction brokerage:** legal in many states with consent; banned in some. Ask what duties you are getting in writing.

### 4.4 Fair housing and valuation ethics
- Valuation must rest on **property characteristics and market evidence**, not on the race, ethnicity, religion, national origin, familial status, disability or other protected characteristics of occupants or neighbors. Comps, "neighborhood desirability" language and AVM features can encode bias; a documented appraisal-bias literature exists. If you suspect a biased valuation, **request reconsideration of value with specific better comps** and consider a second appraisal and a fair-housing complaint route (HUD, state agency).
- **Steering** (nudging people toward or away from areas by protected class) is illegal for agents; buyers can ask for neutral criteria (price, commute, schools by objective data, flood zone) to search.

### 4.5 The money layer (2026 numbers)
- **Conforming loan limit (one unit):** **$832,750** baseline for 2026 (+$26,250); **high-cost ceiling $1,249,125**; 4-unit baseline $1,601,750.
- **FHA limit:** floor **$541,287** (65% of the baseline), ceiling **$1,249,125** for one-unit homes.
- **Mortgage rate (Freddie Mac PMMS, 30-yr fixed):** 6.01% on Feb 19, 2026 (the 2026 low); 6.43% Jul 2; 6.71% Sep 3; 7.03% Sep 24; **7.28% Oct 1** (⚠️ last figure via Trading Economics citing Freddie Mac; confirm on freddiemac.com/pmms). PMMS reflects 20%-down, excellent-credit borrowers; **your quote will differ** (shop at least 3 lenders).
- **Why rates are in a *concepts* skill:** value is what a payment-constrained buyer pool will pay (§7 → `homeval-market-analysis-and-timing`). When rates rise, the *same house* is worth less to the marginal buyer, even if no recent comp shows it yet.

---

## §4A. Checklist: Before You Quote Any Value

- [ ] Purpose stated (list price? offer? refinance? tax appeal? estate?)
- [ ] Effective date stated (today? contract date?)
- [ ] Property rights (fee simple? leasehold? HOA/condo?)
- [ ] Financing assumption (cash-equivalent? concessions?)
- [ ] Scope: what you did NOT see (interior? permits? title?)
- [ ] Evidence listed (comps, dates, adjustments) and an **error band**
- [ ] Disclaimer: not an appraisal; not USPAP; for decision support
