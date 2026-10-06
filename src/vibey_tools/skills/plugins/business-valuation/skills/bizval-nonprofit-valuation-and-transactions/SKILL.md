---
name: bizval-nonprofit-valuation-and-transactions
description: "Use when valuing, merging, acquiring, affiliating with, selling assets of, converting or dissolving a non-profit: why there is no equity price (no owners; assets held in charitable trust), the value concepts that do exist (fair-value net assets, unencumbered net assets, restricted funds, intangibles, mission-continuity and synergy value), transaction types (statutory merger, consolidation, asset transfer, parent/subsidiary affiliation, program transfer, joint venture, dissolution, sale or conversion to for-profit), valuation methods and their limits, private benefit/private inurement and IRC 4958 excess-benefit rules including the rebuttable presumption of reasonableness, state attorney-general and court approvals, donor-restriction and cy-pres issues, grant and contract novation, the diligence checklist and red flags, process timeline and integration."
---

# Company and Non-Profit Valuation: Non-Profit Valuation and Transactions

> **Part 7 of 9** of the *Company and Non-Profit Valuation* reference (plugin `business-valuation`), covering §31–§34. Sibling skills: `bizval-concepts-standards-and-market-structure` (§0–§4), `bizval-market-analysis-and-timing` (§5–§9), `bizval-valuing-a-private-company` (§10–§15), `bizval-buyer-playbook` (§16–§20), `bizval-seller-playbook` (§21–§25), `bizval-diligence-startups-public-and-disputes` (§26–§30), `bizval-nonprofit-financial-health-and-impact` (§35–§38), `bizval-reference` (§39–§43). Code: `scripts/bizval.py` (`np_adjusted_net_assets`, `np_ratios`, `np_runway`, `sroi`).
>
> **Currency:** Legal frameworks are stable but **state-specific**; sector conditions are **October 2026** (§35).

> **⚠️ Scope.** Educational; **not legal, tax or accounting advice.** Non-profit transactions are regulated by state law (attorney general, courts), the IRS, funders and donors. **Engage non-profit counsel and an auditor/CPA before any term sheet**; in sales to for-profit entities, an **independent appraiser** is normally required.

> **The three ideas:**
> 1. **⚠️ A non-profit has no owners, so there is no equity to buy.** Its assets are held for charitable purposes. Transactions transfer **mission, programs, restricted assets and liabilities**, and every term is tested against **fiduciary duty, private benefit and donor intent**, not "what price can we get" (§31).
> 2. **⚠️ Net assets are a ceiling on what you can rely on, not a price.** In the toolkit example, **book net assets of $1.40M** became **$1.45M at fair value** and only **$1.15M "unencumbered"** after purpose restrictions: and that is before diligence finds liabilities (§33).
> 3. **⚠️ Any deal that benefits an insider or a for-profit must pass a fair-market-value process.** Excess-benefit transactions trigger **25% (disqualified person) and up to 200% (uncorrected) excise taxes**; the safe path is the **rebuttable presumption of reasonableness**: *conflict-free approval, comparability data, contemporaneous documentation* (§33.4).

---

## §31. What "Value" Means for a Non-Profit

### 31.1 Why equity valuation doesn't apply
- **No shares, no dividends, no owner:** surplus stays in the organization; **assets must remain dedicated to charitable purposes** (and, on dissolution, go to another exempt organization or government purpose under the dissolution clause and state law).
- **Boards are fiduciaries** (duties of **care, loyalty and obedience** to mission). They approve transactions **for the organization's charitable benefit**, not for a price.
- **A "buyer" of a non-profit** is another non-profit (usually) or, in a sale of assets, a for-profit that pays **fair market value** with proceeds staying charitable.

### 31.2 Value concepts that do exist
| Concept | Meaning | Use |
|---|---|---|
| **Book net assets** | Assets − liabilities per financial statements (two classes: **with / without donor restrictions**) | Starting point |
| **Fair-value net assets** | Assets and liabilities restated to fair value | Merger/asset-sale baseline |
| **Unencumbered (available) net assets** | Fair-value net assets less **donor-restricted** and non-transferable items, contingent liabilities, deferred maintenance | What a successor can actually use |
| **Replacement/program value** | Cost to rebuild the program and relationships | Strategic acquisitions of programs |
| **Intangibles** | Brand, donor relationships, government contracts, accreditation, staff expertise | Often non-transferable or consent-dependent |
| **Synergy/mission-continuity value** | Savings and impact gained by combining; value of avoiding closure | Board decision-making, funder support |
| **Social value (SROI)** | Monetized outcomes ÷ investment | Impact communication; **judgment-heavy** (§37) |
| **For-profit FMV** | Price in a sale of operating assets to a for-profit | **Legal requirement** for sales to non-exempt buyers or insiders |

### 31.3 Limits on transferability (checks before pricing anything)
- **Donor restrictions** (purpose/time; permanent endowment under **UPMIFA**) **follow the money:** they can't be redirected to a new mission without donor consent or **court-approved cy pres / modification**.
- **Government grants/contracts** are often **non-assignable** (agency consent/**novation**) and tied to eligibility, audits (Single Audit) and compliance history.
- **Licenses, accreditations, tax exemptions** (e.g., **property-tax exemption**) don't automatically transfer.
- **Donor lists/privacy:** fundraising data may be subject to donor-privacy commitments and law.
- **Pension, lease, debt and bond covenants** can restrict change of control.

---

## §32. Transaction Types

| Type | What happens | Typical use | Key regulatory/legal points |
|---|---|---|---|
| **Statutory merger** | One entity survives; the other dissolves into it | Full combination of similar missions | **Board and (if membership) member votes**; **state filings**; **AG notice** in many states; **successor liability** |
| **Consolidation** | Two entities form a **new** entity | Equal-partner combination, fresh brand | New 501(c)(3) determination/transfer of exemption; more paperwork |
| **Asset transfer/acquisition** | Acquirer takes selected programs/assets/liabilities | Rescue of a program; avoids unknown liabilities | **Donor restriction compliance; contract novation**; transferor may dissolve or continue |
| **Parent–subsidiary (sole-member affiliation)** | Parent becomes sole member of subsidiary; both survive | Shared governance/back office with brand retention | **Reserved powers**, board composition, **liability separation** |
| **Joint venture / shared services / fiscal sponsorship** | Contractual collaboration; no combination | Testing fit; cost-sharing | **Private-benefit** and **UBIT** review; **grant-compliance** |
| **Program transfer** | One organization hands off a program | Strategic exit from a line of work | Funder/regulator consent |
| **Dissolution and distribution** | Orderly wind-down; assets to another exempt org per dissolution clause | No viable path | **State dissolution process**, **AG/court oversight**, **Schedule N** reporting; **creditors first** |
| **Sale/conversion to for-profit** | For-profit buys operating assets, or entity converts (e.g., hospitals, health plans, schools) | Capital needs; strategic exits | **FMV by independent appraiser; AG (and often court) approval; proceeds fund a charitable foundation/successor**; **excess-benefit and private-benefit tests**; **health-care transaction notice laws** in some states |
**Accounting:** **ASC 958-805** distinguishes **mergers** (no acquirer identified; carryover-type accounting for the combined entity) from **acquisitions** (acquirer identified; acquisition method, fair-value allocation): **confirm with the auditor** because it affects balance-sheet presentation and goodwill.
**Antitrust:** non-profits are not categorically exempt; **HSR filing thresholds** and **state AG reviews** may apply, especially in **health care, higher education and human services markets**.

---

## §33. Valuation Methods in Non-Profit Transactions

### 33.1 Merger and asset-transfer valuation (no price)
| Method | How | Limits |
|---|---|---|
| **Adjusted net assets** | Fair-value assets − liabilities − contingent − deferred maintenance; then subtract **restricted/non-transferable** amounts (`np_adjusted_net_assets`) | **Not a price;** shows what's available and **who brings solvency** |
| **Financial health comparison** | Compare **months of cash/LUNA, revenue concentration, surplus margin, debt** (§36) | Frames **terms**: who is rescuing whom |
| **Synergy model** | `Net synergy = recurring savings + retained/enhanced revenue − dis-synergies (staff/donor attrition) − one-time integration costs` | **Savings are often smaller and slower than expected;** research is mixed: model integration costs explicitly and treat savings as upside |
| **Mission/impact value** | SROI or cost-per-outcome; **funders' perspective** | Judgment-heavy (§37) |
**Verified example:** total assets **$2.3M**, liabilities **$0.9M** → **book net assets $1.40M**; **fair-value adjustments +$0.35M** (real estate), **contingent liabilities $0.12M**, **deferred maintenance $0.18M** → **fair-value net assets $1.45M**; **purpose-restricted $0.30M** → **unencumbered $1.15M**.

### 33.2 Terms in lieu of price
**Governance** (board seats, name/brand, mission statement), **program continuity commitments**, **employment guarantees** (term, comp), **asset restrictions honored** (named funds), **liabilities assumed**, **integration funding**, **timeline**, **break-up rights**, **funder commitments** (merger funds, transition grants), **donor communications plan**, **real-estate/lease handling**, **pension/benefit treatment**, **dispute resolution**.

### 33.3 Sale of operating assets to a for-profit (FMV required)
Use **income** (DCF of the *transferred* cash flows with a market-participant discount rate, §12), **market** (comparable sales; per-bed/per-student/revenue multiples where established), **asset** (appraised assets), and **cost** approaches by an **independent qualified appraiser**, **with documentation** of assumptions and comparable data. **Negotiate for FMV, not "what the charity needs."** Proceeds should fund a **charitable successor/foundation**; **no insider** may receive an undue benefit.

### 33.4 Private benefit, private inurement, and §4958 excess-benefit transactions
- **Private inurement:** no part of net earnings may benefit insiders; **private benefit:** activities must serve public, not private, interests (**more than incidental** private benefit can jeopardize exemption).
- **IRC §4958 (public charities and 501(c)(4)s):** **excess benefit transactions** between the organization and a **disqualified person** (generally those with substantial influence in the last 5 years, family members, and controlled entities) trigger **excise taxes**: **25% of the excess benefit on the disqualified person, 200% if not corrected in time, and 10% (up to $20,000 per transaction) on managers who knowingly approved** (⚠️ verify current amounts and definitions with counsel).
- **Rebuttable presumption of reasonableness** (Treasury Regs. §53.4958-6): (1) **approved in advance by an authorized body composed entirely of individuals without a conflict of interest**; (2) the body **relied on appropriate comparability data**; (3) **adequately and concurrently documented** (minutes within a reasonable period). **Use it for:** executive compensation/severance in a merger, sales of property to insiders, leases with board members, **transaction bonuses**.
- **Conflict-of-interest policy** and **Form 990 Schedule L** (transactions with interested persons) support the record.

---

## §34. Process, Diligence and Integration

### 34.1 Process (typical 6–18 months; funder timelines vary)
1. **Strategic fit and board readiness** (mission alignment, financial need, alternatives).
2. **Confidential exploration** (**MOU/LOI**, non-binding except confidentiality, no-shop and cost-sharing; **board approval to explore**).
3. **Due diligence** (§34.2) with **counsel and auditors**.
4. **Terms and valuation** (§33).
5. **Governing-body approvals; member votes** if applicable.
6. **Regulatory filings and approvals:** **state AG notice/approval** where required, **court approvals** for restricted funds, **funder/agency consents**, **IRS notifications** (updated EIN/exemption records; **Form 990 Schedule N** for dissolutions and significant dispositions).
7. **Closing and integration** (100-day plan).

### 34.2 Diligence checklist (non-profit-specific)
| Area | Key questions | Red flags |
|---|---|---|
| **Financial** | **Audited statements, Form 990s** (3–5 years), **budget vs actual**, **liquidity (months of cash/LUNA)**, **reserves**, **debt**, **cash tied up in reimbursements** | Going-concern doubt; recurring deficits; restricted funds spent on operations (**borrowing from restricted**) |
| **Revenue** | Concentration, **government dependence**, **grant terms/renewals**, donor retention, **pledge collectability** | One funder >30–40%; **federal funding at risk** (§35) |
| **Compliance** | **Single Audit findings, grant compliance**, **UBIT**, **state charity registration**, lobbying/political rules | Questioned costs; overdue filings; **revoked exemption** |
| **Liabilities** | **Pension underfunding, deferred maintenance, litigation, lease obligations, bond covenants, employment claims** | Unrecorded liabilities; unfunded post-retirement benefits |
| **Governance** | Board independence, **conflict-of-interest policy**, **related-party transactions (Schedule L)**, executive comp, whistleblower, **D&O insurance** | Insider deals; weak oversight; staff turnover at top |
| **Programs/impact** | **Outcomes data**, **client satisfaction**, **licensing/accreditation**, **reputation** | Mission drift; program quality issues |
| **People** | Key staff, **comp vs market**, **collective bargaining**, **retention**, **WARN** | Leader-dependent relationships |
| **Real estate/assets** | **Title, zoning, condition, restrictions, property-tax exemption** | Reverter clauses; contamination |
| **IT/data/privacy** | Systems, security incidents, **donor data** compliance | Data breach history |
| **Donor/funder** | **Intent and consent** for restricted funds; **funder reactions** | Donor withdrawal risk |

### 34.3 Integration (first 100 days)
**Leadership and structure** announced early, **employee and client communication**, **donor stewardship plan** (thank, inform, **honor restrictions**), **systems/finance integration**, **program continuity**, **culture work**, **KPIs** (retention, service volume, cost per outcome), **post-merger review at 12–24 months**.

### 34.4 Merge, affiliate, or dissolve? (decision table)
| Situation | Typical path |
|---|---|
| **Healthy, overlapping mission, one stronger** | Merger or acquisition by the stronger |
| **Unique programs, weak back office** | **Shared services/parent–subsidiary** |
| **Program valuable, organization failing** | **Program transfer/asset acquisition** |
| **No viable path; cash running out** | **Orderly dissolution** while assets can still be distributed to mission-aligned recipients (**sooner is better:** delay burns restricted funds and goodwill) |
| **Capital-intensive; needs outside investment** | **Joint venture or sale to for-profit** at FMV with charitable proceeds (heavy regulatory review) |
**Sector context (Oct 2026):** merger activity is **rising** amid federal funding disruptions; advisors expect **closings to outpace mergers** in the near term for organizations that cannot or will not combine (§35).

---

## §34A. Non-Profit Transaction Checklist

[ ] Mission fit and alternatives documented [ ] Board has independent, conflict-free decision-makers [ ] Counsel engaged (non-profit, tax, health/education if relevant) [ ] Audited financials + 990s reviewed [ ] **Restricted funds mapped and honored** [ ] Grant/contract consents plan [ ] Liabilities (pension, deferred maintenance, litigation) quantified [ ] **FMV appraisal for any for-profit or insider element** [ ] §4958 rebuttable-presumption process followed [ ] AG/court/IRS/state filings calendared [ ] Donor/funder communications [ ] Integration plan and funder support
