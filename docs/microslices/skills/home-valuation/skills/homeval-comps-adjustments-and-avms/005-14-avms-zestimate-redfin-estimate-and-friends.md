---
id: skill-14-avms-zestimate-redfin-estimate-and-friends-e9012a6ff4
purpose: 14 avms zestimate redfin estimate and friends
source: src/vibey_tools/skills/plugins/home-valuation/skills/homeval-comps-adjustments-and-avms/SKILL.md
requires: ["skill-13-hedonic-regression-cross-check-6b10a51487"]
links: ["skill-15-worked-example-sandbox-verified-and-the-recipe-for-any-house-e63c6e4331"]
---

## §14. AVMs: Zestimate, Redfin Estimate and Friends

### 14.1 Published accuracy (the honest numbers)
- **Zillow (own published, accuracy data refreshed Aug 8, 2026): median error 1.78% for on-market homes and 7.20% for off-market homes.** (Other Zillow-cited snapshots in 2026 ranged 1.9–2.4% on-market and 6.9–7.5% off-market. ⚠️ Trade press repeats different vintages; use the live Zillow page.)
- **Redfin Estimate:** reported at ~**1.98%** on-market and ~**7.66%** off-market (older published figure).
- **By geography:** off-market median error varies widely by state (e.g., ~5.3% in Colorado vs ~12.7% in Vermont in Zillow's Apr 2026 table; ⚠️ third-party summary); **rural/thin markets: 8–12%+** is reported.
- **Why on-market is 4× better:** the estimate incorporates the **list price, description and photos**, i.e., it partly copies the human CMA. An off-market Zestimate is the real model.

### 14.2 What "median error" means
Half of estimates are **worse** than the median; the tail is much worse. On a $430,000 home, 7.2% = **±$31,000** for the *median* case. Zillow publishes the share within 5%, 10% and 20% of the sale price: **check the within-10%/within-20% shares for your metro** to see tail risk. Do not interpret "±median error" as a confidence interval for your house; it's roughly a 50% interval (§15.4).

### 14.3 How to use AVMs well
1. **Collect 3–5** (Zillow, Redfin, Realtor.com, Cotality/CoreLogic, a county value, HouseCanary or bank tool). **Their spread is an uncertainty signal**: wide spread → model doesn't know your house.
2. **Correct the inputs:** beds, baths, GLA, lot, upgrades, year, condition. Claim your home on Zillow and edit facts; Redfin lets you update details.
3. **AVMs lag turning points** and cannot see: kitchen quality, layout flaws, view, road noise, deferred maintenance, additions. Treat AVMs as the *first screen*, not the answer.
4. **Never use an AVM alone to price, offer or refinance.** Use it to decide whether to invest a weekend in a real analysis.
5. **LLMs are not valuation tools.** A language model with no comps data will *fabricate* a plausible number. Use an LLM for structure (checklists, drafting, code) but feed the numbers from real sales data. Same standard for any "AI CMA" product: ask what comps and what error rate.

---
