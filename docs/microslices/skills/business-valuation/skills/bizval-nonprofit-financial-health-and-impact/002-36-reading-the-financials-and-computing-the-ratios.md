---
id: skill-36-reading-the-financials-and-computing-the-ratios-d30b7ab7e2
purpose: 36 reading the financials and computing the ratios
source: src/vibey_tools/skills/plugins/business-valuation/skills/bizval-nonprofit-financial-health-and-impact/SKILL.md
requires: ["skill-35-the-non-profit-environment-october-2026-snapshot-1332d6bb1a"]
links: ["skill-37-effectiveness-impact-and-charity-evaluation-8396e2aad8"]
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
