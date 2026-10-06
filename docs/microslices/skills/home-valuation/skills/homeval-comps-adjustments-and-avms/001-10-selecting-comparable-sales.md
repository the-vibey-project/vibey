---
id: skill-10-selecting-comparable-sales-3f9beb7273
purpose: 10 selecting comparable sales
source: src/vibey_tools/skills/plugins/home-valuation/skills/homeval-comps-adjustments-and-avms/SKILL.md
requires: []
links: ["skill-11-the-adjustment-grid-32fe32ede4"]
---

## §10. Selecting Comparable Sales

### 10.1 The priority-ordered rules
Rank candidates; do not just filter. **Hard guardrails** (relax only with a written reason) then **ranked similarity**.

| Criterion | Standard starting guardrail | Widen when… | ⚠️ Pitfall |
|---|---|---|---|
| **Status** | **Closed** arm's-length sales | Support only with active/pending (§10.3) | **List prices are not comps.** They are asks |
| **Recency** | ≤ 90 days ideal; ≤ 6 months acceptable | Thin market: ≤ 12 mo with time adjustment | Stale comps in a moving market are the most common error (§12) |
| **Distance** | ≤ 1 mile (urban/suburban) | Rural: 3–10+ miles | Don't cross school-zone, flood-zone, busy-road, HOA or municipal-tax lines without adjusting |
| **Size (GLA)** | ± 10–20% | Large/unique homes | GLA measured differently (use ANSI Z765 logic); below-grade ≠ GLA |
| **Style / design** | Same (ranch with ranch) | Few comps | Cross-style comps need larger adjustments |
| **Age / quality** | ± 10–15 years and same quality tier | Thin market | A renovated 1970s house is closer to newer than to its unrenovated twin |
| **Condition** | Same band (5-point scale you apply consistently) | Always adjust if different | **Flips as comps for unrenovated homes** = overvaluation |
| **Beds/baths/garage/lot** | ± 1 bed / ± 1 bath / same garage count | – | Count above-grade only |
| **Property rights / type** | Same (fee simple SFR vs SFR) | Never mix | Condo vs SFR, leasehold vs fee, new vs resale: different markets |
| **Transaction type** | Exclude REO/short sales/relatives/estate quick-sales *unless the market is distressed* | Distress-heavy local market | Non-market sales understate value |

### 10.2 Ranking score
`homeval.score_comps()` computes a transparent similarity score: normalised gaps in distance, recency, GLA, age, beds, baths, condition, lot and style, with heavier weight on GLA, condition and location. **Keep the score components visible** so you can explain *why* a comp ranked where it did; an unexplainable rank is a black box you will not defend in negotiation.

### 10.3 How many, and the supporting cast
- **Minimum:** 3 closed comps; **good practice:** 5–6, plus **supporting evidence**: (a) *active listings* (the competition and the ceiling), (b) *pending* listings (current demand, price per `pending` date), (c) *expired/withdrawn* listings in the last 6 months (prices the market rejected). **A price above the cheapest comparable active listing that is better is a price that will not sell.**
- **Bracket the subject:** ideally comps both above and below on key features (size, condition, price). A set all *smaller* than the subject forces extrapolation.
- **Use the same tie-breaker an appraiser does:** *which would a buyer of this house pick instead?* That is the substitution principle.

### 10.4 Data hygiene
Verify each comp with at least two sources (MLS or portal + county recorder). Check: sale date vs recording date, **concessions** (sellers paid X), **financing** (seller financing, assumption, buydown), **GLA vs permitted** (unpermitted additions), **lot** (usable vs gross), **condition** from photos (kitchen/baths/flooring/roof), **days on market**, price history (cuts, relists).

---
