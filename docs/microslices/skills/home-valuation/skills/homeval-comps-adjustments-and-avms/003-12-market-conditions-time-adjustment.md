---
id: skill-12-market-conditions-time-adjustment-974917e649
purpose: 12 market conditions time adjustment
source: src/vibey_tools/skills/plugins/home-valuation/skills/homeval-comps-adjustments-and-avms/SKILL.md
requires: ["skill-11-the-adjustment-grid-32fe32ede4"]
links: ["skill-13-hedonic-regression-cross-check-6b10a51487"]
---

## §12. Market-Conditions (Time) Adjustment

**Problem:** a comp that sold 5 months ago reflects the market 5 months ago. In a market moving +/−0.5% per month that is ±2.5%; during a rate shock (§7) it can be larger.

**Methods (use at least two):**
1. **Paired resales:** the *same house* selling twice (repeat sales) is the cleanest signal.
2. **Regression on sale date** (log price per sf on months, `time_adjustment_pct_per_month()`): noisy with fewer than ~30 sales.
3. **Index:** metro Case-Shiller / FHFA HPI / Zillow ZHVI / Cotality HPI monthly changes.
4. **Live evidence:** pending list-to-contract prices and active listing price cuts show where the market is *now*; if pending sales are below recent closings, drift is negative even if the index is lagging.
5. **Sanity cap:** ±0.5%/month is a plausible range outside crises; extrapolating 2–3%/month from a seasonal bump is a classic error.

⚠️ **Do not apply an annual appreciation rate mechanically in a market with a rate shock.** Re-estimate after any move of ~0.5+ points in rates.

---
