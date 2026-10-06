# Car Valuation Plugin

Car valuation and market research for buying and selling a car: the many meanings of a car's "value" (MSRP, invoice, transaction price, retail, private-party, trade-in, instant offer, wholesale, insurance ACV, collector), who produces which number and how they differ, the sales channels and the rules of the game; researching the car market through the Manheim index, transaction prices, days' supply, incentives and loan data; valuing one specific vehicle with comparables, an adjustment grid, a regression cross-check and the guides, including EVs, classics and branded titles; the buyer and seller playbooks; and pre-purchase diligence, fraud patterns, total cost of ownership, lease versus buy, EV versus gas and consumer remedies.

One reference, split into 7 skills along its section groups so a task loads only the part it needs. Section numbers (§0–§35) are shared across the set and cross-references into a sibling skill are written as §N → `skill`. Dated material (indices, prices, loan data, credits, fees and rules) is current to October 6, 2026 and quarantined in a few sections so the durable method does not rot; claims resting on a single or commercially motivated source are marked ⚠️. Companion to the `home-valuation` and `business-valuation` plugins. Educational and procedural, not legal, tax, lending, insurance or mechanical advice.

## Skills

| Skill | Sections | Use it for |
|---|---|---|
| `carval-concepts-methods-and-market-structure` | §0–§4 | What "value" means for a car, approaches, who produces which number, channels, FTC Used Car Rule, fees, tax/credit rules |
| `carval-market-analysis-and-timing` | §5–§9 | Funnel procedure, Manheim/KBB/loan indicators and their pitfalls, segments, regimes, **Oct 2026 snapshot** |
| `carval-valuing-a-specific-vehicle` | §10–§15 | Comps, adjustment grid, regression, guides, EV/classic/branded-title cases, **verified worked example** |
| `carval-buyer-playbook` | §16–§20 | Budget, financing, OTD negotiation, F&I, private-party purchase, decision rules |
| `carval-seller-playbook` | §21–§25 | Payoff/equity, channel comparison by net cash, prep, scam-proof sale process, special cases |
| `carval-diligence-risk-and-ownership-economics` | §26–§30 | PPI, history/title, fraud, TCO, lease vs buy, EV vs gas, specialty, remedies |
| `carval-reference` | §31–§35 | Misconceptions, **what moved (Oct 6, 2026)**, canon/data sources, formulas, method/confidence |

## Toolkit

`scripts/carval.py` needs only `numpy` and `pandas`. From this plugin's directory, `python3 scripts/test_carval.py` simulates a used-car market with known true prices and asserts the tools recover them (median error over 120 random subjects: naive average 4.4%, adjusted comps 1.1%, regression 1.1%, triangulated 0.7%).

## Refresh policy

Method is stable. Update **§32 of `carval-reference` first** (Manheim, ATP, loans, negative equity, EV credits/prices, fees, rules), then §4.3–§4.4 and §9.3. Items marked ⚠️ single-source should be verified before reuse. All default percentages in the toolkit are placeholders.
