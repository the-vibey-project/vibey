---
id: skill-33-canon-and-data-sources-b0db6b0c4c
purpose: 33 canon and data sources
source: src/vibey_tools/skills/plugins/car-valuation/skills/carval-reference/SKILL.md
requires: ["skill-32-what-moved-verified-october-6-2026-469b08c94a"]
links: ["skill-34-quick-reference-31c8ef42d5"]
---

## §33. Canon and Data Sources

**Theory and evidence**
| Source | Why |
|---|---|
| **Akerlof (1970), "The Market for 'Lemons'," *QJE*** | The foundational paper on adverse selection in used cars (why asymmetric information depresses prices) |
| **Bond (1982, *AER*)**, used pickup trucks; **Genesove (1993, *JPE*)**, wholesale used cars | Empirical tests: the lemons effect is weaker or context-dependent in practice |
| **FTC Used Car Rule (16 CFR Part 455)** | The Buyers Guide requirement and as-is rules |
| **Federal Odometer Act (49 U.S.C. ch. 327)** | Odometer disclosure and tampering law |
| **Hagerty Price Guide / Valuation Tools** | Condition-graded collector values and auction data |

**Free/public data (check definitions every time)**
| Source | Use |
|---|---|
| **Cox Automotive Insights** (coxautoinc.com/insights) | Manheim Used Vehicle Value Index, mid-month and monthly; KBB ATP reports |
| **Kelley Blue Book** (kbb.com; mediaroom.kbb.com) | ATP, used prices, instant cash offers, cost to own |
| **Edmunds** (edmunds.com; press room) | Negative equity, transaction data, True Cost to Own |
| **iSeeCars** (iseecars.com) | Model-level depreciation and resale studies |
| **Experian Automotive; NY Fed Household Debt and Credit** | Loan size, terms, delinquency |
| **FRED** (fred.stlouisfed.org): e.g., `TOTALSA`, `CUSR0000SETA02` | Vehicle sales and used-car CPI (confirm series IDs) |
| **NHTSA** (recall lookup by VIN; ratings) | Recalls and safety |
| **NMVTIS / NICB VINCheck** | Title brands, theft/salvage checks |
| **IIHS; Consumer Reports; J.D. Power** | Safety and reliability |
| **FTC consumer advice; CFPB; state AG** | Rights, scams, complaints |
| **fueleconomy.gov** | MPG/EV efficiency data for running-cost calculations |

**Optional connector:** **CarGurus** (listing search and detail; authless). If you install it, `vehicle-listing-search` and `vehicle-listing-detail` can supply live local comps for §10; asking prices only, so apply §12 adjustments.

---
