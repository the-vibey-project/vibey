---
id: skill-34-quick-reference-31c8ef42d5
purpose: 34 quick reference
source: src/vibey_tools/skills/plugins/car-valuation/skills/carval-reference/SKILL.md
requires: ["skill-33-canon-and-data-sources-b0db6b0c4c"]
links: ["skill-35-method-7be2b4a69f"]
---

## §34. Quick Reference

### 34.1 Formulas
```
Loan payment       = P · r / (1 − (1+r)^−n),  r = APR/12
Total interest     = payment · n − P
OTD price          = vehicle + doc fee + add-ons + sales tax + title/reg − trade − rebates
Sales tax (net-of-trade states) = rate × (vehicle + doc + add-ons − trade)   (verify your state's base)
Lease payment      = (cap − residual)/n + (cap + residual) × MF ;   APR ≈ MF × 2400
Residual           = MSRP × residual%;  Cap cost = price − cap reduction + fees
Rebate vs APR      → compare TOTAL cash paid: down + payments (rebate: loan at your market APR; promo: loan at promo APR)
Adjusted comp      = Price + Σ adjustments (comp → subject; superior comp → subtract)
Mileage adj        = (comp miles − subject miles) × $/mile
Equity             = market value − loan payoff  (negative = underwater)
TCO per mile       = (depreciation + interest + taxes/fees + running) ÷ miles
Cost of waiting    ≈ monthly depreciation % + monthly market drift % (plus carrying costs)
EV $/mi            = kWh/mi × blended $/kWh ;  gas $/mi = $/gal ÷ mpg
```

### 34.2 Thresholds (heuristics; calibrate locally)
| Item | Value |
|---|---|
| Comps | 6–10 (≥3 sold); same trim; year ±1; miles ±20–25k; 100–250 mi; ≤60–90 days |
| Adjustment QC | Flag gross adjustments > ~20% |
| Asking → sale | 2–5% dealer; 3–8% private (placeholders; calibrate) |
| Used days' supply | <35 hot; 35–55 firm/balanced; >55 soft; >70 falling |
| Mileage bands | 60k / 100k / 150k (listing-filter cliffs) |
| PPI | ~$100–$250; always for used (incl. CPO) |
| Repair vs replace | Repair if < ~50% of value and root-cause fix |
| 20/4/10 | ≥20% down, ≤48 months, total transport ≤10% of gross (guardrail only) |
| Funds verification | Never release title/keys until funds are cleared at the bank |
| Closing documents | Bill of sale ×2; title signed correctly; odometer statement; **release of liability** filed |

### 34.3 Picker
| Question | Go to |
|---|---|
| What does "value" mean here? | §1–§3 |
| What are my rights as a car buyer? | §4.2, §30 |
| Is it a good time to buy/sell? | §5–§9, §32 |
| What's this car worth? | §10–§15 |
| Should I trust KBB/Edmunds? | §14.1 |
| EV battery/used EV | §14.2, §28.3 |
| Classic/collector | §14.4, §29.3 |
| What do I offer / how do I negotiate? | §18 |
| Financing, term, negative equity | §16.2, §20.2 |
| Dealer fees and add-ons | §4.3, §19.1 |
| Private-party purchase steps | §19.3 |
| Sell: which channel? | §22 |
| Sell: paperwork and scams | §24 |
| Inspection/history/title | §26 |
| Fraud patterns | §27 |
| TCO, lease vs buy, EV vs gas, repair vs replace | §28 |
| Lemon law/complaints/repo | §30 |

### 34.4 Red flags (any three = slow down)
- [ ] Price far below comps; no VIN; seller won't allow a PPI
- [ ] Name on title ≠ seller; "title in the mail"; lien not disclosed
- [ ] History shows brand/odometer anomaly; wear doesn't match mileage
- [ ] Dealer won't give an itemized OTD in writing; add-ons "required"
- [ ] Monthly-payment-only negotiation; 84-month term; negative equity rolled in
- [ ] Spot delivery with "pending financing"
- [ ] Buyer overpays, wants a courier, or uses payment screenshots/escrow they propose
- [ ] EV with no battery report; hybrid with unknown service history

---
