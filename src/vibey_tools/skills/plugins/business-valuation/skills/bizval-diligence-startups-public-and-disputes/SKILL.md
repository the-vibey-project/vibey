---
name: bizval-diligence-startups-public-and-disputes
description: "Use when stress-testing a company deal or valuing special situations: deep diligence tests and red-flag table, earnings fraud and misrepresentation patterns and protections (reps, escrow, R&W insurance); venture-backed startups (stage valuations, post-money math, dilution, SAFEs, venture method, liquidation preferences, down rounds, 409A, QSBS); public-company valuation basics (price vs value, multiples, reverse DCF, equity-risk-premium compression, takeover premiums, fairness opinions); financial-reporting and ESOP valuations (ASC 820/805/350, 409A); and valuation in disputes (divorce, shareholder oppression and appraisal, buy-sell agreements, estate/gift, damages) where state law sets the standard of value."
---

# Company and Non-Profit Valuation: Diligence, Startups, Public Companies and Disputes

> **Part 6 of 9** of the *Company and Non-Profit Valuation* reference (plugin `business-valuation`), covering §26–§30. Sibling skills: `bizval-concepts-standards-and-market-structure` (§0–§4), `bizval-market-analysis-and-timing` (§5–§9), `bizval-valuing-a-private-company` (§10–§15), `bizval-buyer-playbook` (§16–§20), `bizval-seller-playbook` (§21–§25), `bizval-nonprofit-valuation-and-transactions` (§31–§34), `bizval-nonprofit-financial-health-and-impact` (§35–§38), `bizval-reference` (§39–§43). Code: `scripts/bizval.py` (`post_money_round`, `safe_post_money_conversion`, `venture_method`, `qsbs_exclusion`, `dcf`).
>
> **Currency:** Diligence and legal-standard concepts are stable. Venture and public-market data are **dated** (§28.2, §29.2).

> **⚠️ Scope.** Educational; **not investment, legal, tax or valuation-opinion advice.** Disputes and statutory valuations require a credentialed valuation expert and counsel; **the standard of value is set by the jurisdiction, not by this reference.**

> **The three ideas:**
> 1. **⚠️ Diligence is repricing, not confirmation.** Every finding should land in one of four buckets: price, structure, pre-close fix, or walk. **Unsupported add-backs and cash-basis books are the most common sources of overpayment** (§26).
> 2. **⚠️ Startup valuation is a negotiation anchored on the last round and the dilution math, not a DCF.** A $12M pre-money round raising $3M gives **20% to the investor**; a 5% pool top-up lowers the *effective* pre-money to **$11.25M**; a **10× investor target with 50% later dilution** implies a **$15M post-money on a $300M exit** (§28).
> 3. **⚠️ In disputes, "value" is whatever the statute and precedent say.** Many states' fair-value standards exclude minority and marketability discounts that FMV (tax) would apply: the same company can have **two different "values" in two courtrooms** (§30).

---

## §26. Deep Diligence: Tests and Red Flags

### 26.1 Financial and operating tests
| Test | What to do | Red flag |
|---|---|---|
| **Revenue proof** | Tie P&L revenue to **bank deposits, sales-tax filings, POS/ERP data, invoices** | Gaps between deposits and reported revenue; round-number invoices |
| **Cutoff and recognition** | Test last/first 10 days; **deferred revenue**; **channel stuffing**; bill-and-hold | Spike in the last month; unusual credit memos after period end |
| **Customer analysis** | Top-20 customers by year, **cohort retention**, price/volume, contract terms, change-of-control | One customer >20%; recent churn of top accounts; verbal contracts |
| **Gross margin** | By product/customer/job; **unabsorbed labor**; **owner doing production** | Margins improving with no explanation; mix shifts |
| **Operating costs** | **Understated expenses** (underpaid staff, deferred repairs, missing insurance) | Wages below market; **related-party** rent/services |
| **Add-backs** | Evidence ladder (§10.2) | "One-time" costs every year |
| **Working capital** | 12–24 monthly balance sheets; **normalize the peg**; seasonality | A/R aging >90 days; inventory obsolescence; stretched payables |
| **Capex** | Maintenance vs growth; **equipment age**; deferred maintenance | Free cash flow flatters by deferring capex |
| **Debt-like items** | Leases, taxes, bonuses, deposits, **deferred revenue**, litigation, earnouts | Unrecorded liabilities |
| **Tax** | 3 years of returns vs financials; **payroll/sales tax compliance**; nexus; classification | Cash-heavy business with low reported income |
| **Cash controls** | Segregation of duties; **theft risk**; inventory counts | Owner "handles everything" |
| **People** | Key-person risk; **comp vs market**; non-competes; classification | Top performer unsigned |
| **IT/cyber** | Systems, security incidents, **data ownership**, privacy | No backups; ransomware history |
| **Legal/IP** | Assignment clauses, **IP chain of title**, open-source compliance (software), licenses, litigation | Founders' IP not assigned to the company |

### 26.2 Red-flag severity ladder
**Fatal/walk:** fraud indicators; unreconcilable cash; **title or ownership defects**; undisclosed major liabilities; **a seller who won't allow verification**. **Reprice:** concentration, owner dependence, deferred capex, margin erosion. **Structure:** earnouts/escrows for uncertain claims. **Fix first:** lease assignment, licensing, key contracts.

---

## §27. Fraud, Misrepresentation and Protections

### 27.1 Common patterns
| Pattern | How it appears | Check |
|---|---|---|
| **Inflated earnings** | Unsupported add-backs; capitalizing expenses; **pro forma "run-rate"** | QoE; compare to tax returns |
| **Cash skim/underreported income** (the reverse) | Low taxable income but high claimed cash | You can't value or finance unreported cash: **no tax returns, no price** |
| **Fake or related-party customers** | Round-trip revenue | Customer calls; third-party confirmation |
| **Channel stuffing / pulled-forward revenue** | Revenue spike pre-sale | Monthly trend; returns after close |
| **Hidden liabilities** | Unpaid taxes, warranty claims, wage/hour exposure | Tax transcripts, lien searches, employee surveys |
| **"Owner works 10 hours" myth** | Sales and delivery depend on the owner | Interviews with staff/customers; calendar review |
| **Lease/license traps** | Non-assignable, expiring, below-market rent that resets | Lease abstract; landlord estoppel |
| **Misleading CIM metrics** | Best-month annualization, "recurring" that isn't | Contract review; cohort data |
| **Broker/marketplace scams** | Fake listings, advance fees | Verify entity and records; **never wire money before a signed LOI and verified counterparty** |

### 27.2 Protections
**Representations and warranties** (financial statements, taxes, compliance, undisclosed liabilities); **indemnification** with **fraud carve-outs** (caps and baskets don't apply to fraud); **escrow/holdback** (**~5–15%** placeholder range, 12–24 months); **R&W insurance** (mid-market and up; retention and exclusions); **earnouts** tied to verified results; **seller note setoff rights**; **lien/UCC searches**; **tax clearance certificates** where available; **condition: payoff letters and lien releases at closing**; **seller's personal guarantee/ongoing role**. **Document everything in writing** and **preserve seller statements** (emails, CIM).

---

## §28. Venture-Backed Startups

### 28.1 How startups are priced
- **Not by DCF.** Early-stage values reflect **round negotiations**, **comparable rounds**, **growth and burn**, **investor competition** and **dilution/ownership targets**, then a **venture method** sanity check.
- **Post-money = pre-money + new money; investor % = new money ÷ post-money.**
- **Option-pool "shuffle":** a required pool top-up is usually **inside the pre-money**, lowering the effective pre-money.

### 28.2 Reference data (dated; no 2026 Carta quarter retrieved)
| Stage | Median pre-money (Carta, trailing 6 months; 2025-vintage) |
|---|---|
| Seed | ~**$15.2M** |
| Series A | ~**$48.9M** (Q3 2025: **$49.3M**) |
| Series B | ~**$115M** |
| Series C | ~**$254M** |
| Series D | ~**$545M** |
**Down rounds:** Carta ~**17%** of new rounds (Q3 2025), down from >20% for much of 2023–Q1 2025; **Cooley Q1 2026: 11.4% down, 86% up** (different sample). **Founders' median equity** ~**56%** at seed and ~**36%** by Series A (Carta). *These are medians from platform samples with AI-round skew; do not use them as a price.*

### 28.3 Verified math (toolkit)
- **Priced round:** pre-money **$12M**, raise **$3M** → **post $15M; investor 20%**; with a **5% post-money pool top-up** in the pre-money → **existing holders 75%; effective pre-money $11.25M**.
- **Post-money SAFE:** **$500k at a $10M post-money cap = 5.0% ownership before new money** (converts at the cap if the round's pre-money exceeds the cap).
- **Venture method:** exit value **$300M**, later dilution **50%**, target **10×** over 7 years (**38.9% IRR**) → **post-money $15.0M; pre-money $12.0M** after a $3M raise.
- **Preference stack:** **liquidation preferences** (1× non-participating is standard; **participating or >1×** shifts value to investors); **common stock** (founders/employees) is worth **less than preferred**: the basis for **409A** valuations.
- **Down rounds:** **anti-dilution** (weighted average vs full ratchet), **pay-to-play**, **cram-downs**, **recaps**; **flat/down rounds** require more care in cap-table modeling.

### 28.4 Startup M&A and exits
**Acqui-hires, asset sales, preferred-stock waterfall**: at modest exits **preferred holders take first**, and **common may receive little**; **management carve-outs** and **earnouts** appear. **QSBS** (§24.3) can make a founder's stock sale dramatically more valuable after tax (**$15M exclusion; 5-year hold** for 100%).

### 28.5 SaaS and recurring-revenue benchmarks (cross-checks only)
Practitioner sources report **private SaaS ~4–5.5× ARR for lower-middle-market deals**, **slow-growth (<15%) SaaS priced on EBITDA (~8–12×)**, and **public SaaS multiples compressed 20–35% in 2025–26** (⚠️ vendor/advisor-sourced, low reliability). **Rule of 40** (growth % + margin %) is a common quality screen. **Prefer recent comparable transactions from DealStats, PitchBook or an advisor.**

---

## §29. Public Companies, Financial Reporting and ESOPs

### 29.1 Public-company valuation basics
- **Price vs value:** markets are efficient *enough* that **beating the market requires a differentiated view**; **a DCF is a tool for the question "what do I need to believe?"**, so use a **reverse DCF** (solve for implied growth/margin at the current price).
- **Multiples:** P/E, EV/EBITDA, EV/FCF, **PEG**; compare to peers and history; **adjust for growth, leverage, accounting, cyclicality**.
- **Quality screens:** **ROIC vs WACC**, **free cash flow conversion**, **balance-sheet strength**, **share count trends**, **capital allocation**, **accounting quality** (accruals, revenue recognition, non-GAAP add-backs).
- **Reading filings:** **10-K/10-Q/8-K/proxy**: MD&A, risk factors, segment data, footnotes (leases, debt, contingencies, **stock comp**).
- **Control transactions:** **takeover premiums** typically 20–40% over unaffected prices (⚠️ varies); **fairness opinions** assess the **fairness of consideration** from a financial viewpoint: *they're opinions for boards, not valuations for you.*
- **Not advice:** none of this is a recommendation to buy or sell a security.

### 29.2 The equity-risk-premium (ERP) problem, October 2026
With the **10-year near 5.3%**, **S&P 500 forward P/E ~19–19.5×** (earnings yield ~5.1–5.3%) and implied **ERP compressed to near or below zero on the simple earnings-yield spread** (secondary sources; **implied ERP ~2.15%** by one measure), **stock prices embed either strong earnings growth or low required returns.** *A valuation framework with a ~5% ERP (Kroll) implies lower multiples than prices show: reconcile by questioning growth assumptions, not by changing the ERP casually.*

### 29.3 Financial-reporting and tax valuations
- **ASC 820** (fair value measurement), **ASC 805** (business combinations: allocate price to identifiable assets/intangibles/goodwill), **ASC 350** (impairment), **ASC 718** (stock compensation). **409A** valuations support **option strike prices** (use a qualified independent appraiser for safe-harbor protection).
- **ESOPs:** **ERISA** requires **adequate consideration** based on an **independent appraiser's FMV**, including **control and marketability** analysis; **annual valuations**; fiduciary duties; **repurchase obligations**.

---

## §30. Valuation in Disputes and Legal Contexts

| Context | Standard (varies by state) | Typical issues |
|---|---|---|
| **Divorce** | State law: FMV or **fair value**; **personal vs enterprise goodwill** distinctions in many states | **Double-dipping** (valuing the business on capitalized earnings, then treating the same earnings as income for support); **marketability discounts** allowed in some states; owner compensation normalization |
| **Shareholder oppression/dissenters' rights** | **Statutory fair value**; many states **disallow minority and marketability discounts** | Valuation date; **proportional share of enterprise value**; synergies excluded |
| **Buy-sell agreements** | **Contract formula** or appraisal | **Stale formulas**; **funding with insurance**; **price vs FMV** mismatch; *tax consequences if the formula isn't respected* |
| **Estate and gift tax** | **FMV** (hypothetical buyer and seller; Rev. Rul. 59-60) | **Discounts** (minority/DLOM) litigated; qualified appraisal; **valuation date** |
| **Litigation damages** | **Lost profits, diminution of value, reasonable royalty** | But-for analysis; **causation**; **mitigation**; present value |
| **Bankruptcy** | Going concern vs liquidation; **plan confirmation** | **Fresh-start**, **adequate protection**, **cram-down values** |
| **Non-profit transactions** | **FMV; private-benefit tests** | §33 → `bizval-nonprofit-valuation-and-transactions` |
**Practice notes:** engage a **credentialed expert early**; **independence matters**; **reports must be reproducible** (data, assumptions, sources); **expect adversarial scrutiny** (cost of capital choices, discounts, normalization); **date matters** (rates moved sharply in September 2026).

---

## §30A. Diligence and Dispute Checklist (one page)

1. **Standard/premise/date** set by the context (contract, statute, court). 2. **Earnings normalized** and **supported**. 3. **Market and income approaches** with sensitivity. 4. **Discounts** supported **or excluded per jurisdiction**. 5. **Fraud/misrep tests** run (§27). 6. **Structure** (reps, escrow, indemnity) matched to risk. 7. **Documentation** retained. 8. **Expert and counsel engaged** where stakes or legal standards require.
