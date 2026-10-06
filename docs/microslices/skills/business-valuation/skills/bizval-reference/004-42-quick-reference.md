---
id: skill-42-quick-reference-984daa27bb
purpose: 42 quick reference
source: src/vibey_tools/skills/plugins/business-valuation/skills/bizval-reference/SKILL.md
requires: ["skill-41-canon-and-data-sources-3289842821"]
links: ["skill-43-method-5be6deffd1"]
---

## §42. Quick Reference

### 42.1 Formulas
```
SDE            = net income + owner comp + interest + taxes + D&A + one-time + personal − one-time income
Adj. EBITDA    ≈ SDE − fully loaded replacement manager
EV (multiple)  = metric × multiple (cash-free, debt-free)
Equity         = EV − debt − debt-like − NWC shortfall + cash
Ke (CAPM+)     = Rf + β·ERP + size + specific          Rf = max(3.5%, spot 20y UST) per Kroll
WACC           = E/V·Ke + D/V·Kd·(1−t)
FCFF           = EBIT(1−t) + D&A − capex − ΔNWC
Gordon TV      = CF_n(1+g)/(r−g);  EV = ΣPV(CF) + PV(TV)
Cap of earn.   = CF(1+g)/(r−g);  cap rate r−g = 1/multiple
Implied r      = CF₁/Price + g
Control prem.  = 1/(1−MD) − 1
Max price (debt)= [CF/DSCR ÷ (annual payment per $)] ÷ (1 − equity%) ÷ (1 + costs%)
DSCR           = cash flow for debt service ÷ annual debt service
Deal PV        = cash + PV(note) + p·PV(earnout) + (1−haircut)·rollover + p·PV(escrow)
Venture post   = exit·(1−dilution)/target multiple
Months of cash = cash ÷ (annual expenses/12);  LUNA = unrestricted NA − net PP&E (±)
Program ratio  = program ÷ total expenses;  cost to raise $1 = fundraising ÷ contributions
HHI            = Σ(share²)
SROI           = PV[qty × proxy × (1−deadweight)(1−attribution)(1−displacement) × decay] ÷ investment
```

### 42.2 Thresholds (heuristics; calibrate)
| Item | Value |
|---|---|
| Main Street | ~2–3.5× SDE (avg ~2.7×; IQR ~1.9–3.5× practitioner) |
| PE middle market | ~7.0–7.3× TTM adj. EBITDA (GF Data) |
| Small-company discount rate | ~12–25% |
| DLOM discussions | ~20–35% (support required; jurisdiction-dependent) |
| DSCR (lenders) | ≥1.25 (often 1.25–1.5) |
| SBA equity | ≥10% of project cost; standby note ≤50% of injection |
| Customer concentration comfort | each <15–20% |
| TV share of DCF | often 60–75% |
| Non-profit months of cash | ≥3 (3–6 if reimbursement-based) |
| Non-profit concentration | no source >30–40%; HHI <0.25 |
| BBB WGA standards | program ≥65%; fundraising ≤35% of contributions |

### 42.3 Picker
| Question | Go to |
|---|---|
| What does "value" mean here? | §1–§3 |
| Which market is my company in? | §4.1 |
| Is it a good time to sell/buy? | §9 |
| What's it worth? | §10–§15 |
| What's the right discount rate? | §12.2 |
| What can I afford to pay/borrow? | §16.2, §19 |
| How do I compare offers? | §18.2, §22.2 |
| How should I structure for tax? | §24 |
| What does diligence need to find? | §20, §26–§27 |
| Startup valuation/dilution? | §28 |
| Dispute/divorce/estate? | §30 |
| Non-profit merger/sale? | §31–§34 |
| Is this charity healthy/effective? | §35–§38 |

### 42.4 Red flags (three = slow down)
- [ ] **Unsupported add-backs or "pro forma" earnings**; **no tax returns/bank statements**
- [ ] **Top customer >20%**; **owner is the business**
- [ ] **Asking price far above comps for size**; a story instead of numbers
- [ ] **Price depends on earnouts/rollover** with unclear metrics
- [ ] **Buyer's financing unproven** (SBA standby-note math doesn't work)
- [ ] **Discount rate ≤10% on a small company**; terminal value >75% of EV
- [ ] **Non-profit:** restricted-fund borrowing; **<2 months of cash**; **>40% from one funder**; **repeat audit findings**; insider transactions without FMV process

---
