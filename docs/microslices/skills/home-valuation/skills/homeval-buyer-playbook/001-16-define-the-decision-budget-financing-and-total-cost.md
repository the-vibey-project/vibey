---
id: skill-16-define-the-decision-budget-financing-and-total-cost-5b4fd8b105
purpose: 16 define the decision budget financing and total cost
source: src/vibey_tools/skills/plugins/home-valuation/skills/homeval-buyer-playbook/SKILL.md
requires: []
links: ["skill-17-search-and-shortlist-02946a8f73"]
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
