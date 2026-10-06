---
id: skill-35-method-7be2b4a69f
purpose: 35 method
source: src/vibey_tools/skills/plugins/car-valuation/skills/carval-reference/SKILL.md
requires: ["skill-34-quick-reference-31c8ef42d5"]
links: []
---

## §35. Method

**Stable material** (valuation framework, adjustment logic, loan/lease/TCO arithmetic, consumer-protection basics) comes from established appraisal and finance practice. **Dated material** (§9.3, §32) comes from searches run **October 6, 2026**.

**Confidence.**
- **High:** valuation framework; Manheim, KBB ATP, Edmunds negative-equity and iSeeCars figures (primary releases); end date of the federal EV credits; all arithmetic (computed and tested).
- **Medium:** Experian loan figures and NY Fed delinquency (secondary summaries); used-EV magnitudes (sources conflict); doc-fee averages and add-on totals (vendor datasets); the auto-loan deduction details; Hagerty summaries (trade press).
- **Low / unverified (flagged inline):** the FTC CARS Rule withdrawal date (single source); gas-price figure (secondary); tariffs; state-specific rules; per-model battery warranties.

**Source quality.** Many 2026 sources on fees, EV values, depreciation and "how to negotiate" are **dealer-data vendors, lead-generation sites or content marketing**: informative, but commercially motivated and sometimes recycling older vintages. I preferred Cox/Manheim, KBB, Edmunds, iSeeCars, the FTC and law-firm/trade summaries, and flagged the rest.

**Three deliberate choices.**
1. **Error bars and adjustments before answers.** The skill leads with *how wrong a naive number is* (4.4% median, 12% at the 90th percentile) and how adjusted comps fix it, because single-number "book value" thinking is the characteristic failure of both buyers and sellers.
2. **Tested code, synthetic truth.** The worked example uses simulated sales so accuracy can be *checked*: adjusted comps 1.1%, regression 1.1%, triangulated 0.7% median error over 120 subjects. ⚠️ **Real data is noisier** (unobserved condition and history; messier listings), and the simulated regression matches the data-generating process, so **expect 2–3× larger errors in practice.**
3. **Dated facts quarantined.** Market, rate and rule-dependent claims sit in §4.3–§4.4, §9.3 and §32 so the durable method in the other sections doesn't rot. **When this reference is next refreshed, update §32 first.**
