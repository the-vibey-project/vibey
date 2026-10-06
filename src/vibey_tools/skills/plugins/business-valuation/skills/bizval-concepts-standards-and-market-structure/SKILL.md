---
name: bizval-concepts-standards-and-market-structure
description: "Use first for any company or non-profit valuation question: standards of value (fair market value, fair value, investment value, liquidation), premises and levels of value (control, marketable minority, non-marketable), enterprise vs equity value, valuation purposes, the three approaches (income, market, asset) and when each applies, who values and by what standards (AICPA SSVS, ASA, NACVA, IRS Rev. Rul. 59-60, ASC 820), how the deal market is segmented by size (Main Street/SDE, lower middle market, middle market, venture-backed, family/ESOP), who the buyers and intermediaries are, standard deal structures and documents (asset vs stock, LOI, QoE, earnouts, working-capital peg, escrow), and why non-profits have no owners and need a different frame. Includes the router for the whole company and non-profit valuation reference."
---

# Company and Non-Profit Valuation: Concepts, Standards and Market Structure

> **Part 1 of 9** of the *Company and Non-Profit Valuation, Market Research, Buying and Selling* reference (plugin `business-valuation`), covering §0–§4. Sibling skills: `bizval-market-analysis-and-timing` (§5–§9), `bizval-valuing-a-private-company` (§10–§15), `bizval-buyer-playbook` (§16–§20), `bizval-seller-playbook` (§21–§25), `bizval-diligence-startups-public-and-disputes` (§26–§30), `bizval-nonprofit-valuation-and-transactions` (§31–§34), `bizval-nonprofit-financial-health-and-impact` (§35–§38), `bizval-reference` (§39–§43). Section numbers are shared across the set; §N → `skill` points into a sibling. Companion code: `scripts/bizval.py` (tested; see §15).
>
> **Currency:** The framework is stable. Market data, rates and rules are dated **October 2026**; §40 → `bizval-reference` lists what moved.

> **⚠️ Scope.** Educational and procedural. **Not investment, legal, tax, accounting or valuation-opinion advice.** A self-run estimate is not a formal valuation for tax, litigation, financing or financial-reporting purposes; engage a credentialed appraiser, attorney and CPA for those. Deal terms, tax and non-profit law vary by state and facts.

> **The three ideas that organize everything here:**
> 1. **⚠️ "Value" has no meaning until you name the standard, premise, level of value, purpose and date.** The same company can be worth materially different amounts to a divorce court, a buyer who sees synergies, the IRS and a lender. Choose and state them first (§1).
> 2. **⚠️ Price is cash flow × a multiple, and the multiple is a price of risk and transferability.** What a buyer pays depends on *earnings that survive the owner*, quality and growth, financing available, and discount rates. Normalizing earnings and testing transferability matters more than debating the multiple (§10–§12).
> 3. **⚠️ Headline price is not value to the seller or cost to the buyer.** Seller notes, earnouts, escrows, rollover and taxes can move the present value of a "$5.25M" offer to **~$4.6M**, below some all-cash bids (§18, §24), and **non-profits have no owners to pay**, so the question is mission continuity, restricted assets and liabilities, not price (§31).

---

## §0. How to Use This Reference (router)

| You are… | Read first | Then |
|---|---|---|
| Unsure what "value" means or which standard applies | §1–§3 | §14 |
| Researching deal markets, multiples, rates, timing | §5–§9 → `bizval-market-analysis-and-timing` | §40 → `bizval-reference` |
| Valuing a private operating company | §10–§15 → `bizval-valuing-a-private-company` | run `scripts/bizval.py` |
| Buying a business | §16–§20 → `bizval-buyer-playbook` | §26–§27 → `bizval-diligence-startups-public-and-disputes` |
| Selling a business | §21–§25 → `bizval-seller-playbook` | §24 tax structure |
| Startup, public company, ESOP, 409A, divorce, shareholder dispute | §28–§30 → `bizval-diligence-startups-public-and-disputes` | |
| Valuing, merging, acquiring or selling a **non-profit** | §31–§34 → `bizval-nonprofit-valuation-and-transactions` | §35–§38 |
| Evaluating a non-profit's health or a charity as a donor/funder/board member | §35–§38 → `bizval-nonprofit-financial-health-and-impact` | |
| Checking a number or claim | §39–§43 → `bizval-reference` | |

**Immediate-use loop (any company, any side):** 1) state purpose, standard, premise, level of value and date (§1) → 2) read the market regime and the cost of capital (§5–§9) → 3) normalize earnings and test transferability (§10) → 4) triangulate market, income and asset approaches (§11–§13) → 5) adjust for discounts/premiums and bridge EV→equity (§14) → 6) test financeability and structure (§16, §19, §24) → 7) diligence (§20, §26) → 8) quote a **range** and a walk-away (§15, §18).

---

## §1. What "Value" Means

### 1.1 Standards of value (pick one)
| Standard | Definition (short) | Typical use | Notes |
|---|---|---|---|
| **Fair market value (FMV)** | Price at which property would change hands between a hypothetical willing buyer and seller, neither compelled, both with reasonable knowledge of relevant facts | Tax (estate, gift, income), ESOPs, many courts | Hypothetical, not a specific buyer's synergies; discounts for lack of control/marketability may apply |
| **Fair value (financial reporting)** | Exit price in an orderly transaction between *market participants* (ASC 820) | Purchase accounting (ASC 805), impairment (ASC 350), stock compensation, 409A-type work | Market-participant assumptions, not entity-specific |
| **Fair value (statutory/legal)** | Defined by state law in appraisal/dissenters' rights and oppression cases | Shareholder disputes | **Varies by state**; many courts exclude minority and marketability discounts |
| **Investment value** | Value to a *specific* buyer given its synergies, financing and risk | Negotiation, acquisition decisions | Can exceed FMV; reflects what *you* can pay |
| **Intrinsic value** | Analyst's estimate of fundamental value from cash flows | Investing | Subjective; depends on inputs |
| **Liquidation value** | Net proceeds if assets are sold (orderly vs forced) | Distress, floors | Lower than going concern when the business is viable |

### 1.2 Premise and level of value
- **Premise:** *going concern* (continues operating) vs *liquidation* (orderly vs forced).
- **Levels of value:** **strategic control** (synergies) ≥ **financial control** ≥ **marketable minority** (public-stock-like) ≥ **non-marketable minority** (private minority stake). Moving down levels applies discounts (minority, lack of marketability); moving up adds premiums (control). **Control premium = 1/(1 − minority discount) − 1** (a 20% minority discount implies a 25% control premium).
- **Enterprise vs equity:** *Enterprise value (EV)* = value of operations to all capital providers (**cash-free, debt-free**); *equity value* = EV − debt − debt-like items + cash (§14.3). Deals are typically quoted as **EV on a cash-free, debt-free basis** with a normalized working-capital peg.

### 1.3 Purpose (determines everything above)
Sale/purchase; financing/collateral; estate and gift tax; buy-sell agreements; ESOP; divorce; shareholder disputes; litigation damages; financial reporting; 409A; insurance; strategic planning; **non-profit transactions** (FMV and private-benefit tests in §33).

### 1.4 Value, price, cost and worth
- **Value** = a standard-specific estimate. **Price** = what a particular buyer and seller agree. **Cost** = what the buyer actually pays after fees, taxes, financing and structure. **Worth to me** = investment value.
- **Seller's side:** *after-tax, risk-adjusted present value of proceeds* (§18, §24). **Buyer's side:** *risk-adjusted return on total cost* (§16, §19).

⚠️ **GOTCHAS**
- **A multiple without its denominator is meaningless.** SDE ≠ EBITDA ≠ cash flow ≠ revenue; **2.7× SDE is not 2.7× EBITDA** (§11).
- **"Cash-free, debt-free" is a convention, not a fact:** negotiate what counts as debt-like (deferred revenue, accrued bonuses, unpaid taxes, capital leases, customer deposits).
- **Discounts are not free:** each requires support in the facts and the standard of value (§14).

---

## §2. The Approaches

| Approach | Core logic | Best for | Weakness |
|---|---|---|---|
| **Income** | Present value of expected cash flows (DCF) or capitalized normalized earnings | Stable/forecastable businesses; cross-check on market multiples | Highly sensitive to discount rate and terminal value (terminal value often **~65%** of DCF EV) |
| **Market** | Multiples from comparable *transactions* or public companies | Most small and mid-sized deals; "what are buyers paying" | Needs real comparables; mismatch on size, growth, quality; transaction terms obscure headline prices |
| **Asset** | Adjusted fair value of assets less liabilities | Holding companies, asset-heavy or distressed firms; **floor** | Misses goodwill and earning power |
| **Hybrid/special** | Excess earnings (formula) method; venture method; option-pricing for equity classes; rules of thumb | Historical tax/legal contexts; startups; sanity checks | **Rules of thumb are cross-checks, not valuations**; the excess-earnings method is widely criticized as imprecise |

**Reconciliation:** weight by reliability and the question. Small owner-operated companies: **market (SDE) + capitalized earnings**, with an asset floor. Mid-market: **market (EBITDA) + DCF**. Startups: **recent rounds/venture method**, not DCF. Holding/real-estate-heavy: **asset**.

---

## §3. Who Values, and By What Standards

| Source | Role |
|---|---|
| **Credentialed valuation analysts:** ASA (American Society of Appraisers), ABV (AICPA), CVA (NACVA), CFA/CPA with valuation experience | Formal valuations, litigation and tax work |
| **Business brokers and M&A advisors** (IBBA, M&A Source, investment banks) | Opinions of value and sales processes; **not appraisals** |
| **Lenders/SBA lenders** | Valuation for loan underwriting (SBA SOP 50 10 8.1 effective Oct 1, 2026 requires independent valuations in certain situations; verify; §19) |
| **Auditors/valuation firms** | Purchase accounting, impairment, 409A |
**Standards and authorities:** **AICPA SSVS No. 1** (VS Section 100), **ASA Business Valuation Standards**, **NACVA Professional Standards**, **USPAP** (for appraisers who adopt it), **IRS Rev. Rul. 59-60** (the classic FMV factors: nature of business, economic outlook, book value, earning capacity, dividend capacity, goodwill, prior sales, comparable public companies) and related rulings (77-287 restricted stock, 83-120 preferred stock), **ASC 820/805/350/718** (financial reporting), **Treasury Regulations** on non-profit excess benefit (§33). **Reports:** *calculation* engagements (limited procedures) vs *valuation* engagements (full conclusion). A broker's opinion is usually the former at best.

---

## §4. Market Structure (US, Oct 2026)

### 4.1 The size ladder
| Segment | Typical size | Earnings basis | Typical buyers | Typical financing | Reference data (Oct 2026) |
|---|---|---|---|---|---|
| **Main Street** | Cash flow (SDE) <~$1M; price often <$1M | **SDE** | Individual owner-operators, small strategic buyers | **SBA 7(a)**, seller note, personal equity | **BizBuySell Q2 2026:** 2,117 closed sales (−10% YoY); average cash-flow multiple **~2.7×**; median price **$349,250**; median cash flow **$155,921**; median revenue **$692,087**; revenue multiple ~**0.7×** |
| **Lower middle market (LMM)** | EBITDA ~$1–10M; EV ~$5–100M | **Adjusted EBITDA** | Independent sponsors, search funds, small PE, strategics | Senior debt, private credit, seller notes, rollover | Rule-of-thumb bands ~3–8× EBITDA with strong size/quality dispersion; **no reliable single LMM multiple** exists |
| **Middle market** | EBITDA ~$10–100M+ | **Adjusted EBITDA** | PE platforms/add-ons, strategics, family offices | Leveraged loans, private credit | **GF Data (PE-backed, $10–500M EV):** **7.0× TTM adjusted EBITDA in Q2 2026** (7.3× Q1; 7.1× H1; 85 deals each quarter) |
| **Venture-backed** | Pre-profit/growth | Revenue/ARR; round pricing | VCs, corporates | Equity | See §28 |
| **Public** | Any | Market cap/EV | Public markets | n/a | S&P 500 forward P/E ~19–20× (§9.3) |
| **ESOP/family** | Any | FMV by independent appraiser | Employees, family | Seller notes, leveraged ESOP | §25 |
**Rule:** **never apply a mid-market multiple to a Main Street company** (e.g., a "13.4×" median for PE deals whose median target had $64.5M EBITDA is irrelevant to a $1M-EBITDA seller).

### 4.2 Buyers
- **Owner-operators** (SBA-financed individuals) pay for *replaceable* cash flow; **search funds/independent sponsors** underwrite with debt and a business-model thesis; **PE platforms** pay for scale and add-on synergy; **strategics** pay for synergies and market position; **family offices** have longer horizons.
- Buyer type changes the price: *strategic control* ≥ *financial control* ≥ *individual owner-operator* (all else equal).

### 4.3 Intermediaries and information
- **Brokers** (Main Street; typically success-fee based), **M&A advisors/investment banks** (LMM and above), **marketplaces** (BizBuySell, BizQuest, Axial for LMM deal flow, specialty marketplaces for SaaS/online businesses).
- **Data:** BizBuySell Insight (free), **DealStats/Pratt's Stats** (paid), **GF Data**, **PitchBook**, **IBBA Market Pulse**, **Carta** (startups), **Kroll** (cost of capital), **Damodaran** (public multiples and ERP, free). Public data are aggregates: **brokers report voluntarily**, so treat as indicative.

### 4.4 Deal documents and structure
- **NDA → teaser/CIM → IOI → management meetings → LOI (non-binding price, structure, exclusivity ~45–90 days) → diligence (QoE, legal, tax, HR, IT) → definitive agreement (APA/SPA/merger) → closing.**
- **Asset sale** (buyer picks assets/liabilities; step-up; seller may bear ordinary income on recapture) vs **stock/equity sale** (liabilities travel; seller usually prefers) vs **merger**; special elections (**338(h)(10)/336(e), F-reorganization**) can give asset-like tax treatment (§24).
- **Price mechanics:** cash at close, **seller note**, **earnout**, **rollover equity**, **escrow/holdback**, **working-capital peg/true-up**, **reps and warranties** (with possible R&W insurance in larger deals), **indemnification caps/baskets**, **non-compete** (enforceability varies by state; sale-of-business non-competes are generally enforceable), **transition services**.

### 4.5 Non-profits: a different frame (preview of §31–§38)
**501(c)(3) organizations have no owners**, so there is no equity to buy or sell. Transactions are **mergers, asset transfers, affiliations (parent/subsidiary), program transfers, joint ventures and dissolutions**, subject to **state attorney-general** oversight, **private inurement/benefit** limits, donor restrictions and (for sales to for-profits) **FMV and independent appraisal**. The core questions are **mission continuity, restricted funds, liabilities and governance**, not price (§31–§34). Evaluating a non-profit as a donor or funder is a financial-health and impact question (§35–§38).

---

## §4A. Checklist: Before You Quote Any Value

- [ ] **Purpose, standard of value, premise, level of value, date** stated
- [ ] **Basis of earnings** defined (SDE / EBITDA / FCF / ARR) and **normalized** (§10)
- [ ] **Market segment** identified (§4.1); comparables from the same size and type
- [ ] **Cost of capital** current (§12; rates have moved: §9.3)
- [ ] **EV vs equity** bridge defined (debt-like items; working-capital peg)
- [ ] **Range + confidence + what moves it** (customer concentration, owner dependence, rates)
- [ ] Disclaimer: informal estimate; not an appraisal or fairness opinion
