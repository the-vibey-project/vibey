---
id: skill-18-value-the-target-and-build-the-offer-8d2662ece0
purpose: 18 value the target and build the offer
source: src/vibey_tools/skills/plugins/home-valuation/skills/homeval-buyer-playbook/SKILL.md
requires: ["skill-17-search-and-shortlist-02946a8f73"]
links: ["skill-19-under-contract-the-due-diligence-timeline-7a1dd26ae0"]
---

## §18. Value the Target and Build the Offer

### 18.1 The three prices
1. **Value range** from §15 (comps + regression + AVMs + live competition).
2. **Payment ceiling** from §16.1 (the number you can carry with reserves).
3. **Walk-away** = `min(payment ceiling, high end of value range × (1 + overpay tolerance))`. Define "overpay tolerance" (0–3%) *in advance* and what unique features justify it (view, lot, school). **Write it down.**
- **Open** = low end of the defensible range (not an insult: *show the three comps that justify it*).
- **Target** = midpoint of range, adjusted for regime (§9.1).

### 18.2 Offer terms (price is only one lever)
| Lever | Strengthens your offer | Cost/risk to you |
|---|---|---|
| **Price** | Higher | Direct |
| **Earnest money** (commonly ~1–3% of price; varies by state/region) | Larger deposit | At risk if you breach/contingencies lapse |
| **Contingencies** (inspection, appraisal, financing, sale-of-home) | Fewer/shorter | **Each waiver transfers risk to you**; never waive financing unless you can fund |
| **Inspection period** | Shorter | Less time to find defects |
| **Closing date / possession** | Match seller's need; rent-back | Moving flexibility |
| **Appraisal-gap coverage** | "Up to $X above appraisal" | Cash exposure (§18.4) |
| **Financing** | Pre-underwritten, cash, larger down | Time/effort |
| **Escalation clause** | Beats unknown bids | Reveals your max; lenders/appraisers still cap by appraisal |
| **Seller concessions asked** | None | Weaker offer in tight markets, stronger tool in buyer-leaning markets |

⚠️ **Avoid "love letters"/personal narratives** where agents or brokerages advise against them (fair-housing exposure); rely on terms.

### 18.3 Tactics by regime (from §9.1 → `homeval-market-analysis-and-timing`)
- **Hot/seller-leaning:** clean financing, tight timelines, price near ceiling *if inside your walk-away*; skip home-sale contingency; offer a rent-back; escalate within limits.
- **Balanced:** negotiate on repairs and credits; ask for rate buydown or closing-cost help in lieu of price cuts; keep inspection and appraisal contingencies.
- **Buyer-leaning (the 2026 national picture):** open below list with comps, request **closing-cost credits or a seller-paid buydown**, extend inspection to 10–14 days, include a **price-reduction-after-inspection clause**, and target **stale listings** (CDOM above median, ≥2 cuts). Redfin's own agents in Sept 2026 described buyers as able to "afford to be picky" and sellers needing to price correctly from the start.
- **Always:** *name the evidence*. "Three closed comps within 0.5 mile at $X–$Y after adjustments; the active listing at $Z is larger and cheaper per square foot."

### 18.4 The appraisal gap
The lender funds the **lower of price or appraised value**. If appraisal < price:
| Option | Use when |
|---|---|
| **Ask for reconsideration of value** with 2–4 better comps and a list of omitted features | Evidence supports a higher value (do it quickly, via the lender) |
| **Renegotiate price** to the appraisal (or split the gap) | Appraisal contingency intact; market supports it |
| **Cover gap in cash** | Only if inside your walk-away and reserves remain |
| **Switch lender/appraisal** | Rarely allowed; time-consuming |
| **Walk** | Contingency intact and price > your walk-away |
`appraisal_gap_plan(offer, appraised, down_payment, cash_reserve)` gives the gap and which options apply.

---
