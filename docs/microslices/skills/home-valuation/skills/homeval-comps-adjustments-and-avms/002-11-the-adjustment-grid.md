---
id: skill-11-the-adjustment-grid-32fe32ede4
purpose: 11 the adjustment grid
source: src/vibey_tools/skills/plugins/home-valuation/skills/homeval-comps-adjustments-and-avms/SKILL.md
requires: ["skill-10-selecting-comparable-sales-3f9beb7273"]
links: ["skill-12-market-conditions-time-adjustment-974917e649"]
---

## §11. The Adjustment Grid

### 11.1 Direction (get this right or every number is backwards)
**Adjust the comp toward the subject.**
- Comp is **superior** to the subject on a feature → **subtract** (negative adjustment).
- Comp is **inferior** → **add** (positive adjustment).
- Example: comp has a third garage bay the subject lacks → subtract the value of a bay. Comp is 150 sf smaller → add 150 × marginal $/sf.

### 11.2 Order (USPAP/URAR sequence)
1. **Transactional adjustments first** (applied in order, each on the cumulative price): **property rights**, **financing terms**, **conditions of sale**, **expenditures immediately after purchase** (deferred maintenance).
2. **Market conditions (time)**, applied to the *adjusted* price (§12).
3. **Then property characteristics**: location, site, view, design/quality, age/condition, GLA, rooms, garage, extras.

### 11.3 Where the numbers come from (in descending reliability)
| Method | How | When to use |
|---|---|---|
| **Paired sales** | Two sales identical except one feature; the price gap ≈ the feature's value | Rich markets; best evidence |
| **Regression (hedonic)** | Coefficients on log price (§13) | ≥ ~50 local sales; controls many features at once |
| **Matched-pair inference from listings** | Compare listings pre/post renovation, or same model homes with/without a feature | Cross-check |
| **Cost-to-cure** | Cost of fixing a defect (not of building the feature new) | Deferred maintenance, defects |
| **Depreciated cost** | Replacement cost new − depreciation | Only when market evidence is absent; it overstates |
| **Survey/rule-of-thumb** (Cost vs Value etc.) | Industry averages | Last resort; ⚠️ these are *survey-based opinions* (§23) |

### 11.4 Typical magnitudes (starting hypotheses ONLY; replace with local evidence)
| Feature | Typical treatment | ⚠️ Caveat |
|---|---|---|
| **GLA** | **~30–50% of the comp's average $/sf** for each marginal sf (marginal sf < average sf) | Using the average $/sf over-adjusts; smaller differences → smaller error |
| **Bathroom** | A bath of a type (full vs half) is worth ~low-to-mid five figures in typical markets; use local pairs | Count above-grade full/half consistently |
| **Bedroom** | Often near zero *after* adjusting GLA; bed count matters at thresholds (3 vs 4) | Adjusting both GLA and beds double-counts |
| **Garage bay** | Low-to-mid four to low five figures | Attached vs detached, door height, workshop |
| **Condition** | ~2–5% of price per condition step on a consistent scale | Largest and most subjective adjustment; document with photos |
| **Lot** | $/sf for *excess usable* land, not gross | Slope, flood, easements, shape |
| **Pool** | Often **near zero or negative** in many climates | Region-dependent; verify locally |
| **Age/updating** | Small per-year effect, large step effects from systems (roof, HVAC) | Overlaps with condition; avoid double counting |
| **Location** | Paired sales across the boundary (school, road, flood) | Often the largest single factor |

`homeval.adjust_comps()` defaults are **placeholders** (e.g., $7,500/bath, $8,000/garage bay, condition at 3% per step, GLA at 40% of $/sf). Override each with local evidence.

### 11.5 Size limits (quality control)
Traditional underwriting guidance flags **net adjustments > ~15%** and **gross adjustments > ~25%** of a comp's price (⚠️ guidelines, not law). `adjust_comps()` marks `OVER-ADJUSTED` above these; drop such comps unless nothing else exists, and say so.

### 11.6 Cash-equivalent adjustments (financing and concessions)
If a seller paid concessions that were reflected in the price, the cash-equivalent price is lower. Simple approach: **subtract seller-paid concessions** (and the value of any below-market seller financing/buydown) from the sale price before other adjustments. Document it; many "paid-over-list" sales evaporate after this step.

---
