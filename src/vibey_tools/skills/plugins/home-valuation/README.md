# Home Valuation Plugin

Home valuation and market research for buying and selling a house: what "value" means and who produces each opinion of it (appraisal, CMA, BPO, AVM, tax assessment), the three approaches, the NAR-settlement-era rules and the UAD 3.6 appraisal change; researching a housing market from macro to street, with each indicator's exact definition and the ways it misleads; valuing one specific house with comparable sales, an adjustment grid, a time adjustment and a regression cross-check, and reading AVM error honestly; the buyer and seller playbooks; and diligence, climate and insurance risk, the income approach for rentals and flips, specialty valuations, fraud and fair housing.

One reference, split into 7 skills along its section groups so a task loads only the part it needs. Section numbers (§0–§35) are shared across the set and cross-references into a sibling skill are written as §N → `skill`. Dated material (rates, loan limits, market statistics, litigation status) is current to October 6, 2026 and quarantined in a few sections so the durable method does not rot; claims resting on a single or commercially motivated source are marked ⚠️. Companion to the `car-valuation` and `business-valuation` plugins. An explanatory and procedural reference, not appraisal, legal, tax, lending or investment advice.

## Skills

| Skill | Sections | Use it for |
|---|---|---|
| `homeval-concepts-methods-and-market-structure` | §0–§4 | What "value" means, the three approaches, who produces value opinions, NAR-settlement-era rules, UAD 3.6 |
| `homeval-market-analysis-and-timing` | §5–§9 | Funnel procedure, indicator definitions and how each lies, rate/insurance effects, regimes, Oct 2026 snapshot |
| `homeval-comps-adjustments-and-avms` | §10–§15 | Comp selection, adjustment grid, time adjustment, regression, AVM error, **verified worked example** |
| `homeval-buyer-playbook` | §16–§20 | Budget from payment, agent agreement, offer ladder, 30-day timeline, rent vs buy |
| `homeval-seller-playbook` | §21–§25 | Net sheet, pricing by regime, prep ROI, offers, taxes, special situations |
| `homeval-diligence-risk-and-investment` | §26–§30 | Diligence, insurance/climate, income approach, specialty valuation, fraud |
| `homeval-reference` | §31–§35 | Misconceptions, **what moved (Oct 6, 2026)**, canon/data sources, formulas, method/confidence |

## Toolkit

`scripts/homeval.py` needs only `numpy` and `pandas`. From this plugin's directory, `python3 scripts/test_homeval.py` runs a synthetic market with a known true price and asserts the tools recover it (comps +0.38%, regression -1.54%, triangulated -0.39%).

## Refresh policy

Method is stable. Update **§32 of `homeval-reference` first** (rates, NAR/Redfin stats, UAD dates, loan limits, litigation status), then §4.5 and §9.3. Items marked ⚠️ single-source should be verified before reuse.
