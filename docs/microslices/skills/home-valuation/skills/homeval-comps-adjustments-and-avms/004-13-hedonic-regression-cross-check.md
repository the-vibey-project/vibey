---
id: skill-13-hedonic-regression-cross-check-6b10a51487
purpose: 13 hedonic regression cross check
source: src/vibey_tools/skills/plugins/home-valuation/skills/homeval-comps-adjustments-and-avms/SKILL.md
requires: ["skill-12-market-conditions-time-adjustment-974917e649"]
links: ["skill-14-avms-zestimate-redfin-estimate-and-friends-e9012a6ff4"]
---

## §13. Hedonic (Regression) Cross-Check

**Model:** `ln(price) = β0 + β1·ln(sqft) + β2·beds + β3·baths + β4·ln(lot) + β5·age + β6·condition + β7·garage + β8·months_since_sale + ε`.

**Why log price:** effects become percentages; heteroscedasticity falls; coefficient on `ln(sqft)` is an elasticity (in the example: 0.84 vs a true 0.85: a **1% bigger house costs ~0.84% more**, not 1%).

**When to run it:** ≥ ~50–100 sales in your market area in the last 6–12 months, same property type. Add **neighborhood/school-zone dummies** if you can.

**Checks (do all):**
- **Hold-out test:** fit on 80%, predict 20%; report median absolute % error (MdAPE).
- **Residual plot:** look for clusters (a street or condition class the model misses), heavy tails, trend with price.
- **Robust standard errors** (the toolkit uses HC0); sign and size sanity on every coefficient (age negative? condition positive?).
- **Outliers:** examine, don't auto-drop (they may be flips or distress).
- **What it cannot see:** condition beyond your scale, finishes, view, layout, deferred maintenance, lot quality. **Condition is the dominant omitted variable in real data**, so treat a regression as a *cross-check on comps*, never the sole answer.

**Interpretation:** `price_band` and `hedonic_predict()` return p10–p90 using the model's residual spread. `approx_mdape_pct = 0.6745 × residual sd × 100` ≈ the typical absolute % error.

---
