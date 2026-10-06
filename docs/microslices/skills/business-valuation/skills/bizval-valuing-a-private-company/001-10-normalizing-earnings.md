---
id: skill-10-normalizing-earnings-8a3a60c967
purpose: 10 normalizing earnings
source: src/vibey_tools/skills/plugins/business-valuation/skills/bizval-valuing-a-private-company/SKILL.md
requires: []
links: ["skill-11-market-approach-ee2503b983"]
---

## §10. Normalizing Earnings

### 10.1 Which earnings?
| Measure | Definition | Used for |
|---|---|---|
| **SDE (Seller's Discretionary Earnings)** | Pre-tax earnings + owner's total compensation + interest + D&A + non-recurring and discretionary/personal items; **earnings to one full-time owner-operator** | **Main Street** (price ÷ SDE) |
| **Adjusted EBITDA** | EBITDA + normalizing adjustments, **after a market-rate replacement for the owner's work** | Lower-middle and middle market |
| **Free cash flow (FCFF)** | EBITDA − taxes on EBIT − capex − Δ net working capital | DCF |
| **Run-rate / pro forma** | Adjusted for known changes (new contract, cost cut) | Negotiation; **buyers discount it heavily** |
**SDE → EBITDA:** `EBITDA ≈ SDE − fully loaded replacement manager cost`. A business with **$202,000 SDE** and a **$75,000** replacement manager has **~$127,000 EBITDA**: it belongs to a different buyer pool and a different multiple.

### 10.2 Add-back evidence ladder
| Evidence | Accepted? |
|---|---|
| **Documented, one-time, third-party-verifiable** (legal settlement invoice, storm repair) | **Yes (high probability)** |
| **Owner personal expenses run through the business** with receipts and tax filings | Often (verify against tax returns) |
| **Owner compensation above market** | Yes, but **replace the owner's labor** (§10.1) |
| **"One-time" expenses that recur** (every year) | **No** |
| **Estimated** future savings; **unpaid family labor**; **cash not reported** | Rarely: unreported cash is not earnings a buyer or lender can underwrite |
| **Related-party rent/pricing at non-market terms** | Adjust to market (up *or* down) |
**Tool:** `quality_weighted_addbacks([(9000,0.9),(14000,0.5),(12000,0.2)])` → **$17,500 accepted of $35,000 claimed**. With a $179,000 base before add-backs (net income $60k + owner comp $95k + interest $8k + D&A $22k − one-time income $6k), **claimed SDE is $214,000, quality-weighted SDE ~$196,500, and SDE with no add-backs $179,000**: a **~$17,500 (8%) swing, which at 2.7× is ~$47,000 of price**.

### 10.3 Quality of earnings (QoE) checklist
- **Revenue:** cutoff, deferred revenue, **customer concentration**, **churn/cohorts** (recurring revenue), pricing vs volume, one-time projects.
- **Margins:** gross margin by product/customer; **owner doing the selling or production**; vendor concentration.
- **Costs:** **maintenance vs growth capex**, deferred maintenance, **under-paid staff** (replacement wages), related-party items, **tax compliance** (payroll, sales tax, worker classification).
- **Working capital:** seasonality, DSO/DPO/inventory, **normalized peg** (§14.3).
- **Cash proof:** **bank statements ↔ tax returns ↔ financials** reconcile; **accrual vs cash basis**; sales tax filings; POS/ERP data.
- **Time:** use **3–5 years** and **TTM**; a **weighted average** (`weighted_average_earnings([100k,120k,150k],[1,2,3]) = $131,667`) for fluctuating earnings; **don't average away a structural decline**.

### 10.4 Transferability tests (valuation drivers that aren't in the P&L)
Owner role (sales, technical, relationships), **key employees** (retention agreements), **customer contracts** (assignable, change-of-control terms), **licenses/permits**, **lease** (assignable, term, rent vs market), **suppliers**, **brand/IP** (ownership chain), **systems/documentation**, **regulatory exposure**. Each failed test should reduce earnings, the multiple or both (§14).

---
