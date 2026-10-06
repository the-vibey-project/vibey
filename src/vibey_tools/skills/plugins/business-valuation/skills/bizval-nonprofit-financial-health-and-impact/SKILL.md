---
name: bizval-nonprofit-financial-health-and-impact
description: "Use when evaluating a non-profit as a donor, funder, lender, board member, auditor or merger partner, or researching the non-profit sector: the October 2026 environment (Giving USA 2026 $617.2B, individuals 64%, bequests +19.7%, OBBBA 2026 giving rules, federal funding disruption, survey stress data), how to read Form 990s and audited statements (net assets with/without restrictions, functional expenses, pledges, reimbursements), the ratio set with formulas, thresholds and interpretation traps (program ratio and the overhead myth, months of cash and LUNA, concentration/HHI, surplus margin, current ratio), a verified stress test, impact measurement (theory of change, cost per outcome, SROI with a 2.67:1 vs 0.69:1 sensitivity), charity evaluators and standards (Charity Navigator Encompass, BBB 20 standards, Candid), and playbooks for funders, boards and leaders."
---

# Company and Non-Profit Valuation: Non-Profit Financial Health and Impact

> **Part 8 of 9** of the *Company and Non-Profit Valuation* reference (plugin `business-valuation`), covering §35–§38. Sibling skills: `bizval-concepts-standards-and-market-structure` (§0–§4), `bizval-market-analysis-and-timing` (§5–§9), `bizval-valuing-a-private-company` (§10–§15), `bizval-buyer-playbook` (§16–§20), `bizval-seller-playbook` (§21–§25), `bizval-diligence-startups-public-and-disputes` (§26–§30), `bizval-nonprofit-valuation-and-transactions` (§31–§34), `bizval-reference` (§39–§43). Code: `scripts/bizval.py` (`np_ratios`, `np_runway`, `hhi`, `sroi`, `np_adjusted_net_assets`).
>
> **Currency:** Analytic method is stable; §35 is an **October 2026** snapshot. Thresholds are **heuristics**.

> **⚠️ Scope.** Educational; **not investment, tax, legal or accounting advice.** Financial ratios are screens, not judgments of an organization's worth or effectiveness. Verify tax-exempt status and registration before giving.

> **The three ideas:**
> 1. **⚠️ Liquidity and concentration kill non-profits faster than "overhead" does.** The example organization has an **82% program ratio** (looks great) but **1.6 months of cash, 1.5 months of liquid unrestricted net assets and 45% government revenue**: losing 30% of government grants (**−$45,000/month**) drains cash from **$520k to $76k in 12 months and below zero in month 15** (§36).
> 2. **⚠️ The overhead ratio is a weak proxy for effectiveness and a driver of the "starvation cycle."** BBB Wise Giving Alliance still verifies **program ≥65% of total expenses** and **fundraising ≤35% of related contributions**, but the sector has long argued that ratios alone mislead; use them as **minimum-compliance screens**, then examine liquidity, concentration and outcomes (§36–§37).
> 3. **⚠️ Impact numbers are judgments.** The same program produced an **SROI of 2.67:1** with moderate assumptions and **0.69:1** with pessimistic ones. Ask for **the counterfactual, the evidence, and the sensitivity range**, not a single ratio (§37).

---

## §35. The Non-Profit Environment (October 2026 snapshot)

### 35.1 Giving (Giving USA 2026, for calendar 2025)
| Item | Figure |
|---|---|
| **Total giving** | **$617.2B** (+5.7% current dollars; **+3.0% inflation-adjusted**); first time above $600B |
| **Individuals** | **$394.2B (64%)**, +4.1% (+1.4% real); share near its lowest on record (80% in 1985); includes ~$100B passing through donor-advised funds (⚠️ secondary); mega-gifts ~**$19.2B** (~4% of individual dollars) |
| **Foundations** | **$117.15B (19%)**, +5.7% |
| **Bequests** | **$62.19B (10%)**, **+19.7%** (+16.6% real): the standout; ~20% of bequest dollars came from estates ≤$1M |
| **Corporations** | **$43.67B (7%)**, +3.1% |
| **By recipient** | Religion **23%**, human services **15%**, education **14%**, foundations **12%** (gifts to foundations **−16.2%**), public-society benefit **11%**, health **~9% ($61.4B)** |
**Reading it:** the *aggregate* is strong, the *structure* is shifting: **fewer, larger donors**; **bequests and mega-gifts** carry the totals; **the everyday donor base is under pressure**; **bequests are volatile and shouldn't be budgeted as recurring revenue.**

### 35.2 Policy and funding stress
- **Federal funding disruption:** advisers estimate **~$49B in grant terminations** through 2025 and **about one-third of non-profits** lost or at risk of losing federal funding (⚠️ insurer/advisor secondary sources); **funding is shifting from federal to state** with **slow reimbursement (60–90 days)**.
- **CEP "State of Nonprofits 2026" (380 leaders):** **~90%** worried about **burnout**, **66%** about **financial stability**, **30% reduced staff**.
- **Nonprofit Finance Fund 2025 survey (cited by CPA sources):** **more than half hold ≤3 months of cash.**
- **Mergers and closures:** merger activity **rising** (esp. health/human services); advisors expect **closures to outpace mergers** (§34.4).

### 35.3 2026 tax changes for donors (OBBBA; effective tax years beginning 2026)
| Rule | Effect |
|---|---|
| **Non-itemizer deduction** | **$1,000 single / $2,000 joint** for cash gifts to public charities |
| **0.5% AGI floor for itemizers** | The first 0.5% of AGI in giving isn't deductible (carryforward 5 years): e.g., **$1M AGI → first $5,000 of giving** |
| **35% cap on value for top-bracket (37%) donors** | Deduction value limited to 35 cents per dollar |
| **60% AGI limit for cash gifts** | Made permanent; 50% for non-cash |
| **Corporate 1% floor** | Gifts below 1% of taxable income are non-deductible (10% ceiling stays) |
**Fundraising implications:** **bunching** gifts, **DAFs**, **appreciated-stock gifts** and **QCDs** (IRA charitable distributions) gain planning value; **small recurring donors** may see little tax benefit; messaging should **not** depend on deductions.

---

## §36. Reading the Financials and Computing the Ratios

### 36.1 Where the data live
| Source | Use | Notes |
|---|---|---|
| **Form 990 / 990-EZ / 990-N** | Public; **revenue (Part VIII), functional expenses (Part IX), balance sheet (Part X), governance (Part VI), compensation (Part VII)**; **Schedule A** (public support), **Schedule L** (related-party transactions), **Schedule O** (narrative) | **Lag** of up to ~1–2 years; often the only data for small orgs |
| **Audited financial statements** (ASC 958) | Net assets **with/without donor restrictions**, **liquidity and availability disclosure**, functional expense table, notes (pledges, endowment, debt, contingencies) | **More reliable** than 990; BBB WGA uses audited statements when available |
| **Single Audit** (federal awards ≥ threshold, ~**$1M** under the 2024 Uniform Guidance revisions, ⚠️ verify) | Compliance findings, questioned costs | Red flag if repeated |
| **Aggregators:** ProPublica Nonprofit Explorer, Candid (GuideStar), IRS **Tax Exempt Organization Search** (status), state AG registries | Quick screens; **verify exempt status and registration** | Many are derived from the 990 |
| **Management/budget/forecast** | Current liquidity; cash forecast (**13-week** is standard) | Ask for it |

### 36.2 Accounting traps
- **Net assets with vs without donor restrictions:** *only unrestricted funds can cover general operations.* **Restricted ≠ available.**
- **Pledges receivable (multi-year)** are recognized **up front** (present value), inflating revenue and surplus without cash; **conditional grants** are recognized when conditions are met; **cost-reimbursement grants** create **receivables and cash lags**.
- **Functional allocation:** **joint costs** and **allocated overhead** can **understate** fundraising or management costs; ratios vary with accounting choices.
- **In-kind and PP&E:** **donated goods/services** inflate revenue and expenses; **net property** isn't liquid.
- **One-time items:** large gifts, **investment gains**, **asset sales**, forgiven loans or pandemic-era relief can mask structural deficits.
- **Fiscal-year and mix effects:** compare **same periods** and **3–5 year trends**.

### 36.3 Ratio set (formulas, heuristics, interpretation)
| Ratio | Formula | Heuristic | Interpretation / trap |
|---|---|---|---|
| **Surplus margin** | (Revenue − Expenses) ÷ Revenue | Slightly positive; **chronic ~0%** can't build reserves | Exclude one-time/non-cash items |
| **Program expense ratio** | Program ÷ Total expenses | BBB WGA **≥65%**; Charity Navigator historically ~70% screens | **Overhead myth:** low overhead can mean **under-investment**; compare by org type |
| **Fundraising efficiency** | Fundraising expenses ÷ Contributions (cost to raise $1) | BBB WGA **≤35%** of related contributions (**≤$0.35**) | Young orgs/events cost more; **example: $0.25** |
| **Months of cash** | Cash ÷ (Annual expenses ÷ 12) | **≥3 months** generally recommended (National Council of Nonprofits); **3–6** if reimbursement-based or volatile | **Example: 1.6 months = fragile** |
| **LUNA / months of LUNA** | Liquid Unrestricted Net Assets = unrestricted net assets − net PP&E (− illiquid board-designated assets + related debt in some variants) ÷ monthly expenses | **≥3 months** | **Example: $500,000 = 1.5 months** |
| **Current ratio** | (Cash + liquid investments + receivables) ÷ Current liabilities | >1.5–2 | Receivables quality (**government reimbursements**) matters: **example 2.44** |
| **Debt ratios** | Total liabilities ÷ assets; debt ÷ unrestricted net assets | Context-dependent | **Example: 0.39; 0.31** |
| **Revenue concentration** | Top source share; **HHI** (sum of squared shares) | **No source >30–40%** (heuristic); HHI <0.25 diversified | **Example: government 45%, HHI 0.35** |
| **Revenue growth vs expense growth** | % change | Revenue ≥ expenses | Growth funded by **restricted or one-time** money is not scale |
| **Donor retention / dependence** | % retained; contributions ÷ revenue | Org-specific | Concentration in a few donors/bequests |
| **Compensation reasonableness** | CEO comp ÷ budget; Schedule J | Peer comparisons | **Excess-benefit** concern if far above comparables (§33.4) |

### 36.4 Verified example (`np_ratios`)
**Revenue $4.0M** (government **$1.8M**, contributions **$1.4M**, fees **$0.6M**, other **$0.2M**); **expenses $3.9M** (program **$3.2M**, fundraising **$0.35M**, management **$0.35M**); cash **$0.52M**; liquid investments **$0.10M**; receivables **$0.60M**; current liabilities **$0.50M**; assets **$2.3M** (net PP&E **$0.8M**); liabilities **$0.9M**; unrestricted net assets **$1.3M**; debt **$0.4M**.
| Ratio | Value |
|---|---|
| Surplus margin | **2.5%** |
| Program expense ratio | **82.1%** |
| Fundraising cost per $ | **$0.25** |
| **Months of cash** | **1.6** |
| **Months of LUNA** | **1.5** |
| Current ratio | 2.44 |
| Debt/assets | 0.39 |
| Government share | **45%** |
| Revenue HHI | **0.35** |
**Stress test (`np_runway`):** monthly expenses **$325k**; recurring revenue **$333k**; lose **30% of government grants (−$540k/yr; −$45k/month)** → monthly revenue **$288k**, burn **−$37k/month**: cash **$616k (base) vs $76k at month 12**, **negative in month 15** (no cuts, no new money). *Screens like "program ratio >65%" would pass this organization; liquidity and concentration say it is one funding shock from crisis.*

---

## §37. Effectiveness, Impact and Charity Evaluation

### 37.1 The impact chain
**Inputs → activities → outputs (what was done) → outcomes (change in people/conditions) → impact (change attributable to the program).** Ask for **outcomes and the counterfactual** (what would have happened anyway), **not outputs** ("meals served") alone.

### 37.2 Evidence quality ladder
**Randomized controlled trials** → **quasi-experimental** (matched comparison, difference-in-differences) → **pre/post with comparison** → **pre/post only** → **testimonials/outputs**. **Beware** selection bias, self-reported outcomes, **short follow-ups**, **organization-run evaluations**, and **outcomes chosen after the fact.**

### 37.3 Cost per outcome and cost-effectiveness
`cost per outcome = total program cost ÷ outcomes achieved`; **compare within the same outcome type**; include **full cost (indirect costs)**; adjust for **difficulty of population served**. For some fields (e.g., global health) **independent cost-effectiveness analyses** exist; for most local services, comparability is limited.

### 37.4 SROI (social return on investment): verified arithmetic
`sroi(outcomes, investment, discount_rate)` values each outcome as `quantity × proxy value × (1−deadweight) × (1−attribution) × (1−displacement)`, decays it by **drop-off**, and discounts it.
**Example program** (investment **$620,000**; 220 participants):
- Outcome A: **$4,500** per participant per year; deadweight **30%**, attribution **20%**; drop-off **20%/yr** over **3 years**.
- Outcome B: **$1,200**; deadweight **15%**, attribution **10%**; **2 years**.
→ **PV of social value $1,653,369 → SROI 2.67 : 1** (3.5% discount rate).
**Pessimistic single-outcome case** ($2,700 proxy; deadweight 50%; attribution 30%; drop-off 30%): **0.69 : 1.**
**Lessons:** **proxies, deadweight and attribution drive the answer**; report a **range**, **name the proxy sources**, and **never compare SROI ratios across organizations** with different assumptions.

### 37.5 Charity evaluators and standards
| Evaluator | What it does | Limits |
|---|---|---|
| **Charity Navigator (Encompass)** | Scores **four beacons**: **Finance & Accountability, Impact & Results, Leadership & Adaptability, Culture & Community** (100-point; ratings by tier); mostly derived from 990 data | Data lags; financial beacon uses ratios; impact beacon is thin for small orgs |
| **BBB Wise Giving Alliance (Give.org)** | **20 Standards for Charity Accountability** (governance, finances, results reporting, appeals); **Standard 8: program ≥65%** and **Standard 9: fundraising ≤35% of related contributions** (uses audited statements where available) | Voluntary participation; ratio thresholds are blunt |
| **Candid (GuideStar) Seal of Transparency** | Reported disclosures (mission, programs, leadership, metrics) | Self-reported |
| **IRS Tax Exempt Organization Search** | Verifies **exempt status**, 990 filing and revocation | Not a quality rating |
| **State AG/secretary-of-state registries** | Charitable solicitation registration and enforcement | Varies by state |
**Scam alert:** **sound-alike names**, **pressure/urgency**, **untraceable payments**: verify **EIN, status and registration** before giving.

---

## §38. Playbooks

### 38.1 Donors and foundations (due diligence scaled to the gift)
- **Small gifts:** verify **status** and **registration**; skim **990** and evaluator pages.
- **Mid-size:** read **3 years of financials**, compute **months of cash/LUNA and concentration**, review **governance** (independent board, conflict policy, audit committee) and **outcomes evidence**.
- **Large/multi-year:** site visit/reference calls, **budget-to-actual**, **reserve policy**, **leadership succession**, **funding-diversification plan**, **theory of change and evaluation plan**.
- **Funding practice:** prefer **multi-year, general operating support**, **cover full costs** (indirect rates; federal de minimis indirect rate reportedly **15%** after the 2024 Uniform Guidance revision: ⚠️ verify), **don't cap overhead**, **fund reserves**, and **pay promptly**. **Under 2026 tax rules**, consider **bunching and DAFs** (§35.3).

### 38.2 Board members and treasurers
Monthly **dashboard**: **months of cash and LUNA**, **13-week cash forecast**, **budget vs actual**, **receivables aging (government reimbursements)**, **revenue concentration**, **pipeline (probability-weighted)**, **restricted-fund tracking**, **covenant compliance**. **Adopt a reserve policy** (**3–6 months**; higher if funding is volatile), **diversification targets** (no source >30–40%), **scenario plans** (**lose the largest grant; 60–90 day reimbursement delay**) with **trigger-based actions**, and **an early "merge or partner" option review** while strong.

### 38.3 Executive directors in a funding shock (first 90 days)
**Cash first:** 13-week forecast; **freeze discretionary spend**; **accelerate receivables**; **negotiate with landlord/lenders**; **secure a line of credit** or **bridge loan** (CDFIs/community lenders) *before* a crisis; **communicate** transparently to staff, funders, donors; **protect core programs**; **evaluate partnerships/mergers** (§34); **fundraise from individuals/bequests** (relationship-based); **document restricted-fund compliance**.

### 38.4 Lenders and funders of capital
Underwrite on **cash flow and liquidity**, **government receivables quality**, **revenue concentration**, **reserves**, **governance**, **collateral/guarantees** (often limited), and **grant assignment** (federal/state contract restrictions). Prefer **flexible, patient capital**; use **covenants tied to liquidity**.

### 38.5 Earned revenue and social enterprise
Fees and enterprise revenue diversify income but bring **UBIT** (unrelated business income tax) risks, **mission drift**, **working-capital needs** and **unit-economics discipline**: **value the enterprise like a company** (§10–§15) *and* test mission fit.

---

## §38A. Non-Profit Financial-Health Checklist

[ ] Exempt status and registration verified [ ] 3–5 years of 990s and audited statements [ ] Months of cash/LUNA computed [ ] Revenue concentration and HHI [ ] Restricted vs unrestricted separated [ ] Receivables (government) aged [ ] Liabilities/pension/deferred maintenance [ ] 13-week cash forecast [ ] Governance and conflicts reviewed [ ] Outcomes evidence and counterfactual [ ] SROI/cost-per-outcome with ranges [ ] Stress test (lose 30% of the largest source) [ ] Funding practice aligned (multi-year, full cost)
