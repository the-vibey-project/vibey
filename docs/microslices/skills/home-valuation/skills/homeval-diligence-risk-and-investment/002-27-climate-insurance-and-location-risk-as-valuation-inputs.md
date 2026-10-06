---
id: skill-27-climate-insurance-and-location-risk-as-valuation-inputs-2ea8f8eeeb
purpose: 27 climate insurance and location risk as valuation inputs
source: src/vibey_tools/skills/plugins/home-valuation/skills/homeval-diligence-risk-and-investment/SKILL.md
requires: ["skill-26-physical-and-legal-due-diligence-62ee53a725"]
links: ["skill-28-the-income-approach-and-investment-math-46f0b9bfaf"]
---

## §27. Climate, Insurance and Location Risk as Valuation Inputs

### 27.1 The data (2026)
- **Average annual homeowners premium projected at ~$3,057 for 2026 (+4% after +12% in 2025); up ~46% since 2021, roughly three times inflation** (Insurify via Bloomberg/press, Mar 2026). Premiums rose in 95% of ZIP codes between 2021 and 2024 (Consumer Federation of America).
- **Cotality projects ~+8% in 2026 and +8% in 2027**; insurance is now ~**9% of the typical homeowner's total payment**, a record share (⚠️ via press summaries).
- **Florida averages roughly $8,300–$8,500** (Insurify), more than double the national average; **2025 increases exceeded 20% in six states** (e.g., Minnesota +34%, Colorado +33%, Nebraska +25%, Oklahoma +24%).
- **Climate exposure:** one analysis (Realtor.com's Hale, press) put share of housing stock facing severe or extreme risk at >6% flooding, ~18% wind and ~6% wildfire; Miami-Fort Lauderdale-West Palm Beach has ~$307B in home value at risk (≈23% of local value).
- ⚠️ **Treat these as trend indicators.** Premium levels depend heavily on state, roof age, construction, deductible and claims history. **Get actual quotes.**

### 27.2 Convert insurance into price
```python
# loan capacity lost by an extra monthly cost, at 7.28%:
extra_monthly = 250
loan_capacity_lost = extra_monthly / hv.monthly_pi(1, 7.28)    # ≈ $36,538
# +$1,000/yr premium → ≈ $12,179 of loan capacity at 7.28%
```
**Valuation logic:** an uninsurable or high-premium house must be **priced down by the capitalised extra cost** (≈ extra monthly ÷ the buyer's payment-per-dollar factor), not by an arbitrary discount. Conversely, a better insurance profile (new roof, impact windows, higher elevation) is a *price-supporting* feature.

### 27.3 Insurance checklist before you commit
- **Get at least 2–3 quotes on the specific address** (not just ZIP); ask about **roof-age rules, wind/hail percentage deductibles, water-backup coverage, replacement-cost vs ACV, ordinance and law coverage.**
- **Check claims history** (CLUE/seller disclosures) and **prior non-renewal**; ask the seller for the current policy declarations and 3-year premium history.
- **Flood:** lender-required in special flood hazard areas; the NFIP's Risk Rating 2.0 pricing is property-specific (elevation, distance to water, replacement cost); private flood may be cheaper or costlier. **Even outside the mapped zone, flood risk exists**: check history, drainage and elevation.
- **State insurers of last resort** (FAIR plans/state wind pools) exist; they can be a fallback with higher cost and lower coverage.
- **Wildfire/wind/hail:** defensible-space, roof class, shutters/impact glass can matter for both premiums and availability.
- **Tools:** FEMA Flood Map Service Center; NOAA/NWS climatology; USGS; commercial property-risk tools (First Street, Cotality). *If the Cotality connector (§33) is installed, `at-get_property_climate_risk`, `at-get_property_roof_age` and `pr-get_home_price_index_forecast` can feed this step.*

---
