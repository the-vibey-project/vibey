---
id: skill-9-regimes-tactics-and-timing-humility-4adc542735
purpose: 9 regimes tactics and timing humility
source: src/vibey_tools/skills/plugins/car-valuation/skills/carval-market-analysis-and-timing/SKILL.md
requires: ["skill-8-segmentation-never-average-across-segments-3357f327ff"]
links: ["skill-9a-market-diagnosis-template-fill-in-one-paragraph-aaed0f8f4f"]
---

## §9. Regimes, Tactics and Timing Humility

### 9.1 Regime table (thresholds are heuristics; calibrate with local data)
| Regime | Used days' supply | Wholesale trend | Listings with cuts | Seller tactic | Buyer tactic |
|---|---|---|---|---|---|
| **Hot** | <35 | Rising >1%/mo | Few | Price at market; list fast; accept good offers | Be pre-approved; decide quickly; verify condition anyway |
| **Firm** | 35–45 | Flat/up | Moderate | Price at comps; strong listing | Shop several; negotiate OTD, not monthly payment |
| **Balanced** | 45–55 | Flat | Moderate | Price to comps; expect 3–5% negotiation on asks | Compare 3+ OTD quotes; use days-on-lot |
| **Soft** | 55–70 | Falling | Many | Price sharply or take instant offer; don't wait | Wait for stale listings; lower offers justified by comps |
| **Falling** | >70 | Falling >1.5%/mo | Most | Sell now; every month costs ~1–2% | Hold cash; prices drop; beware catching knives |

### 9.2 Leading indicators (check weekly while buying/selling)
1) Manheim mid-month reading → 2) MMR 3-year-old index → 3) local days-on-lot and price-cut frequency for your model → 4) new-car incentives → 5) loan approval/APR changes → 6) gas price → 7) recall/redesign news for your model.

### 9.3 Snapshot: United States, October 2026 (re-pull before relying)
| Metric | Reading | Source / date |
|---|---|---|
| Manheim Used Vehicle Value Index | **206.2** mid-Sept (−1.0% MoM; **−0.4% YoY**, first YoY decline of 2026); Aug **208.2** (+0.4% YoY); Jul 210; Jun 212.9; **Mar peak 215.3 (+6.2% YoY)** | Cox Automotive (Sep 18, 2026; Q2 release) |
| MMR 3-Year-Old Index | **−0.8%** since the start of September (sharper than the same period last year; slightly above long-term average) | Cox, Sep 18 |
| Cox year-end outlook (set mid-year) | MUVVI to finish 2026 ~**+2%** vs year-end 2025 ("normal seasonal pattern") | Cox Q2 release ⚠️ may be revised |
| New-vehicle ATP | **$50,089** Aug (+0.5% MoM, **+1.9% YoY**); average MSRP **$51,852**; incentives **6.5%** of ATP; new EV ATP **$54,813** (−2.7% YoY); new-car inventory **2.68M** units | KBB/Cox, Sep 10 |
| Used-vehicle average sale | **$27,239** Aug (highest since Dec 2022); dealer used supply **44 days** | KBB, Sep 2026 |
| Loans (Q2 2026) | New avg **$43,610 / $765 / 69.5 mo**; used **$27,852 / $542 / 67.9 mo**; approvals ~three-quarters of applications | Experian (via secondary); KBB |
| Negative equity (Q2) | **29.6%** of trade-ins; avg **$6,884**; those buyers' new-loan payment **$944** vs **$777** average; projected interest **$16,270** vs **$9,811** | Edmunds, Jul 16, 2026 |
| Used EVs | Cox avg listing **$37,441** (Aug, +8.2% YoY); used EV share of Manheim units **>4%** record (July) | Cox/Recurrent; ⚠️ partly secondary |
| 5-yr depreciation | **41.8%** average (best: trucks/hybrids; worst: EVs/luxury) | iSeeCars, Mar 2026 |
| Collector cars | Hagerty Market Rating near **~15-year low**; condition-#3 values down ~0.5% book-to-book | Hagerty (via trade press) |

**Reading it:** wholesale values have **given back the spring bounce** and are now slightly below last year; new-car prices are rising slowly with incentives shrinking; loans are easier to get but heavily leveraged (record negative equity); **segment divergence is large** (EVs and compacts firm; trucks/SUVs soft). For **buyers**, the second half of the year is typically better than spring on used prices; for **sellers**, the spring window has passed and wholesale is drifting down, so *waiting costs money* (§9.4).

### 9.4 Timing humility (and the cost of waiting)
- **A depreciating asset rarely rewards waiting.** If wholesale is falling ~1%/month and the car loses ~1–1.5%/month in value (age/mileage/market), selling 3 months later costs ~3–5% of value plus insurance, parking and opportunity cost. Use `carval.retention_curve()` for the age effect; use the Manheim trend for the market effect.
- **For buyers, waiting works only if** you have a good alternative (current car is reliable), the market is *falling*, and financing/rates are not rising. A model-year changeover is the classic good time to buy the outgoing year new.
- **Avoid forecasting** a "used-car crash" or "spike" as a decision rule; use scenario ranges (±5%) and buy/sell at a price that works at the *low* end.
- **Mileage clocks tick:** each month of ownership adds ~1,000 miles; sell before crossing a mileage band (60k/100k).

---
