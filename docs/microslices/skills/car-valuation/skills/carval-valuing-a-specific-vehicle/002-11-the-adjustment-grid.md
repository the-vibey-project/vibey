---
id: skill-11-the-adjustment-grid-3f81a46a6c
purpose: 11 the adjustment grid
source: src/vibey_tools/skills/plugins/car-valuation/skills/carval-valuing-a-specific-vehicle/SKILL.md
requires: ["skill-10-selecting-comparable-cars-b96b3bf475"]
links: ["skill-12-time-season-and-the-asking-to-sale-gap-0a97015647"]
---

## §11. The Adjustment Grid

### 11.1 Direction
**Adjust the comp toward the subject.** Comp is **superior** (lower mileage, better condition, newer) → **subtract**. Comp is **inferior** → **add**.

### 11.2 Adjustment items and where the numbers come from
| Item | Treatment | Source of number (best → worst) |
|---|---|---|
| **Asking → expected sale** | Active listings: −X% (placeholder 3%) | Your market's sold/asking ratio; price-cut history; dealer feedback |
| **Time/market drift** | Compound monthly drift to today | MUVVI/MMR trend; regression on date (§12) |
| **Mileage** | (comp miles − subject miles) × **$/mile** | **Estimate from the comps** (`mileage_adjustment_per_mile()`); guides; ~cents/mile for mainstream cars, rising with value (the test market's truth is ≈ $0.05/mile at ~$21k) |
| **Year** | % per model year (placeholder 7%) | Paired comps one year apart |
| **Trim/options** | $ amount from paired comps (trim difference); only count options buyers pay for | Paired comps; guide option values |
| **Condition** | % per step on your rubric (placeholder 3%/step) | Condition-matched pairs; cost-to-cure for visible defects (tires, brakes, paint, interior) |
| **Accident history** | % per reported accident (placeholder 6–7%) | Matched pairs; **severity matters** (structural/airbag deployment ≫ cosmetic) |
| **Owners** | ~1% per additional owner | Matched pairs; a weak effect after controlling for age/miles |
| **CPO / warranty** | $ premium (placeholder $1,500) | CPO vs non-CPO matched pairs; warranty value |
| **Title brand** | Large discount (§14.5) | Branded vs clean comps |
| **Service records/deferred maintenance** | Cost-to-cure | Shop quotes (tires, brakes, timing belt, fluids) |
| **Modifications** | Usually **no add** or a discount; returns to stock may cost | Enthusiast sales (BaT) for desirable mods |

### 11.3 Quality control
Flag comps with **gross adjustments above ~20% of price** (`adjust_listings()` marks `OVER-ADJUSTED`). **Rank by lowest gross adjustment** and weight accordingly (`reconcile()`).

---
