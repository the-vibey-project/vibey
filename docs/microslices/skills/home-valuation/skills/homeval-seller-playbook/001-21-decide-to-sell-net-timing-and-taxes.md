---
id: skill-21-decide-to-sell-net-timing-and-taxes-503d0fedd8
purpose: 21 decide to sell net timing and taxes
source: src/vibey_tools/skills/plugins/home-valuation/skills/homeval-seller-playbook/SKILL.md
requires: []
links: ["skill-22-pricing-strategy-19f77c4af2"]
---

## §21. Decide to Sell: Net, Timing and Taxes

### 21.1 The net-proceeds sheet (build it before you call an agent)
```python
import homeval as hv
hv.seller_net(price=429_100, mortgage_payoff=210_000, listing_comm_pct=2.5, buyer_comm_pct=2.5,
              seller_concessions_pct=1.5, transfer_tax_pct=0.2, title_escrow_pct=0.5,
              prep_costs=4_500, repairs_credit=2_000, prorated_taxes_hoa=1_200)
```
**Verified output:** commissions $21,455; concessions $6,437; transfer tax $858; title/escrow $2,146; prep $4,500; repairs credit $2,000; prorations $1,200 → **total costs $38,595 (9.0% of price)** → **net $180,505** after a $210,000 payoff.

| Scenario (payoff $210k, same cost assumptions) | List/Sale | Concessions | Costs % | **Net** |
|---|---|---|---|---|
| A | $440,000 | 0% | 7.5% | **$197,220** |
| B | $429,100 | 1.5% | 9.0% | $180,505 |
| C | $420,000 | 0% | 7.5% | $178,360 |
| D | $415,000 | 3.0% | 10.6% | $161,195 |
⚠️ **Lessons:** concessions are real money; a lower-priced clean offer can beat a higher-priced offer with concessions; commission treatment (§24.2) swings costs by a point or more. Typical total selling costs run roughly **6–10% of price** (⚠️ commission ranges are practitioner-reported; get quotes).

### 21.2 The cost of waiting
`carrying_cost_of_waiting(monthly_piti, monthly_utilities, months, price, monthly_drift_pct)`:
- Carry $2,900 + $300 utilities × 3 months = **$9,600**.
- Expected price change over 3 months at **−0.2%/mo = −$2,569** (net −$12,169); at **+0.2%/mo = +$2,580** (net −$7,020).
- **Waiting is rational only if the expected monthly price gain exceeds carry ÷ price (~0.75%/mo here).** In a flat or falling market it is rarely worth it, *unless* you can rent the house out profitably or you're not carrying the payment.

### 21.3 The lock-in effect and replacement cost
Many owners hold sub-4% mortgages. **P&I per $100k at 3.5% is $449 vs $684 at 7.28%.** Selling means trading a $1,347 payment (a $300k 3.5% loan) for ~$1,700 on a $248,595 loan *even after* moving to an equal-priced home with $180,505 equity as the down payment (the example above). That cost is your real "price of moving." **Decide with replacement cost, not just sale price.** Sequencing options:
| Sequence | Pros | Cons |
|---|---|---|
| **Sell, then buy (rent in between)** | Clean; known equity; stronger buyer on the next purchase | Double move; rent; market risk on the buy |
| **Buy, then sell (bridge/HELOC)** | Move once; shop calmly | Two payments; qualification; risk of selling lower |
| **Contingent purchase (sale-of-home contingency)** | Limits risk | Weak offers in competitive markets |
| **Sell with rent-back/late closing** | Time to find the next home | Buyer must accept; insurance/occupancy terms |

### 21.4 Taxes (US federal; educational; consult a CPA)
- **Section 121 exclusion:** up to **$250,000 (single) / $500,000 (married filing jointly)** of gain on your **principal residence**, if you **owned and used it as your main home for 2 of the 5 years** before sale and haven't used the exclusion on another sale in the prior 2 years. **Thresholds are not indexed to inflation** and have been unchanged since 1997. I found no 2026 enactment changing them (the "No Tax on Home Sales Act" and similar bills have been proposed; ⚠️ verify current law).
- **Gain** = (sale price − selling costs) − **adjusted basis** (purchase price + qualifying closing costs + capital improvements). **Keep receipts for improvements** (additions, roof, HVAC, kitchens) to raise basis. `home_sale_gain()` estimates the taxable gain above the exclusion.
- **Partial exclusion** (job change, health, unforeseen circumstances): prorated by months/24 (e.g., 15 months → 15/24 × $250,000 = $156,250).
- **Complications:** depreciation recapture if part of the home was rented or used for business; divorce/death rules; **state taxes** (some states don't conform; e.g., ⚠️ one source says PA doesn't recognize §121 treatment: verify); **inherited property gets a stepped-up basis** to fair market value at the date of death (very different gain, valuation date matters: get an appraisal as of that date).

---
