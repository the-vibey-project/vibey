---
id: skill-43-method-5be6deffd1
purpose: 43 method
source: src/vibey_tools/skills/plugins/business-valuation/skills/bizval-reference/SKILL.md
requires: ["skill-42-quick-reference-984daa27bb"]
links: []
---

## §43. Method

**Stable material** (standards of value, approaches, normalization, deal structure, non-profit legal frameworks) reflects established valuation and transaction practice. **Dated material** (§9.3, §28.2, §35, §40) comes from searches on **October 6, 2026**.

**Confidence.**
- **High:** valuation framework; GF Data and BizBuySell figures (reported summaries of primary releases); Giving USA 2026; QSBS and charitable-deduction rules; all arithmetic (computed and tested).
- **Medium:** rates and Fed details (primary news plus secondary pages that disagreed in places); SBA SOP details (advisor summaries); S&P valuation (secondary); non-profit stress data (advisor/survey summaries).
- **Low / unverified (flagged inline):** the 20-year Treasury input; the $10M SBA cumulative limit; startup data for 2026; SaaS multiples (vendor sources); owner-dependency discounts; Single Audit and indirect-rate thresholds; §4958 dollar amounts.

**Source quality.** Many 2026 pages on multiples, SBA rules and "how to sell your business" are **broker or advisor marketing**; they're useful but commercially motivated, sometimes self-contradictory (e.g., multiples quoted as 2.65× or 2.7×; PitchBook vs MergerMarket volumes), and occasionally stale (one rate page still showed pre-hike values). I preferred primary releases (BizBuySell, GF Data via ACG, Giving USA, Kroll, CNBC) and flagged the rest.

**Three deliberate choices.**
1. **Show the error of the naive method first.** The synthetic test shows a median multiple missing EV by **16.4% (90th percentile 36.9%)** and a size-band median by **12.1%**, versus **1.7%** for a regression that recovers the true drivers: the central lesson for private-company pricing. ⚠️ **Real data is noisier and the regression is correctly specified in the simulation: expect 2–3× larger errors in practice.**
2. **Treat structure and tax as part of value.** Present value of structured offers (~87.5% of headline), **$170,000** asset-vs-stock tax difference, and QSBS cliffs change decisions more than a half-turn of multiple.
3. **Treat non-profits as a separate problem, not a "for-profit with no profit."** They have no owners; the key questions are **restrictions, liabilities, liquidity, concentration and mission continuity**: the framework in §31–§38 uses **fair-value and unencumbered net assets, §4958 process, and ratio stress tests** instead of price.
**When this reference is next refreshed, update §40 first** (rates, Kroll inputs, multiples, SBA rules, Giving USA, tax rules), then §9.3, §28.2 and §35.
