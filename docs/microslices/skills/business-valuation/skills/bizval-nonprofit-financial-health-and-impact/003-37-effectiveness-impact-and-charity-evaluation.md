---
id: skill-37-effectiveness-impact-and-charity-evaluation-8396e2aad8
purpose: 37 effectiveness impact and charity evaluation
source: src/vibey_tools/skills/plugins/business-valuation/skills/bizval-nonprofit-financial-health-and-impact/SKILL.md
requires: ["skill-36-reading-the-financials-and-computing-the-ratios-d30b7ab7e2"]
links: ["skill-38-playbooks-bd6d67c40c"]
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
