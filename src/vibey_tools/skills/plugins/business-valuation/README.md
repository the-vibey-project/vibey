# Business Valuation Plugin

Company and non-profit valuation, market research, buying and selling: standards, premises and levels of value, the income, market and asset approaches, who values and by what standards, and the size-segmented deal market with its documents; researching deal markets and multiples and how each indicator misleads; valuing a private company (normalized earnings, a regression of multiples, WACC and DCF, the asset approach, discounts and the EV-to-equity bridge); the buyer and seller playbooks, including deal structure, financing and taxes; deep diligence, fraud, venture-backed startups, public companies, 409A, ESOP and disputes; and non-profits treated as their own problem, with no owners and no equity price: transactions, IRC 4958, Form 990 and ratio analysis, stress tests and impact measurement.

One reference, split into 9 skills along its section groups so a task loads only the part it needs. Section numbers (§0–§43) are shared across the set and cross-references into a sibling skill are written as §N → `skill`. Dated material (rates, equity risk premium, deal multiples, SBA rules, tax rules, giving data) is current to October 6, 2026 and quarantined in a few sections so the durable method does not rot; claims resting on a single or commercially motivated source are marked ⚠️. Companion to the `home-valuation` and `car-valuation` plugins. Educational and procedural, not investment, legal, tax, accounting or valuation-opinion advice.

## Skills

| Skill | Sections | Use it for |
|---|---|---|
| `bizval-concepts-standards-and-market-structure` | §0–§4 | Standards/levels of value, approaches, who values, size-segmented deal market, deal documents; non-profit frame |
| `bizval-market-analysis-and-timing` | §5–§9 | Research funnel, indicators and their pitfalls, drivers (rates!), regimes, **Oct 2026 snapshot** |
| `bizval-valuing-a-private-company` | §10–§15 | Normalizing earnings, multiples regression, WACC/DCF, discounts, EV→equity, **verified worked examples** |
| `bizval-buyer-playbook` | §16–§20 | Affordability, sourcing, LOI/structure, SBA and other financing, LBO sensitivity, diligence, closing |
| `bizval-seller-playbook` | §21–§25 | Readiness, pricing, advisors/process, LOI comparison (PV), asset vs stock, QSBS, alternatives |
| `bizval-diligence-startups-public-and-disputes` | §26–§30 | Deep diligence, fraud, startups, public-company basics, 409A/ESOP/ASC, disputes |
| `bizval-nonprofit-valuation-and-transactions` | §31–§34 | No-owner frame, merger/affiliation/dissolution/for-profit sale, FMV, §4958, diligence |
| `bizval-nonprofit-financial-health-and-impact` | §35–§38 | Sector snapshot, Form 990/audit reading, ratios and stress test, SROI, evaluators, playbooks |
| `bizval-reference` | §39–§43 | Misconceptions, **what moved (Oct 6, 2026)**, canon/data sources, formulas, method/confidence |

## Toolkit

`scripts/bizval.py` needs only `numpy` and `pandas`. From this plugin's directory, `python3 scripts/test_bizval.py` runs verified examples on synthetic data with known truth (e.g., a multiples regression recovers the true drivers: 1.7% median EV error vs 16.4% for a median multiple and 12.1% for a size-band median; DCF identity checks; deal PV; SBA debt capacity; LBO sensitivity; asset-vs-stock and QSBS arithmetic; startup and non-profit calculations).

## Refresh policy

Method is stable. Update **§40 of `bizval-reference` first** (rates, Kroll ERP/risk-free, BizBuySell/GF Data, SBA SOP, tax rules, Giving USA, non-profit stress data), then §9.3, §28.2 and §35. Items marked ⚠️ single-source should be verified before reuse. Every default percentage in the toolkit is a placeholder.
