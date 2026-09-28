---
id: skill-10-arbitrage-real-vs-apparent-cb8fd0a07f
purpose: 10 arbitrage real vs apparent
source: src/vibey_tools/skills/plugins/trading-mechanics/skills/trading-styles-arbitrage-forex-and-defi/SKILL.md
requires: ["skill-9-day-trading-d6ef257b70"]
links: ["skill-11-forex-acf0791b23"]
---

## §10. Arbitrage — Real vs Apparent

**⚠️ True arbitrage is a riskless profit from simultaneous offsetting positions, and it is
essentially extinct at retail scale** — ⚠️ **because it is the single thing every
professional firm is best equipped to find, and it disappears in microseconds.**

```
Cross-exchange       ⚠️ requires capital pre-positioned on BOTH venues, and transfer
                     latency is exactly what kills it
Triangular (FX)      §11
Cash-and-carry       spot vs futures — ⚠️ this is a financing trade, and the return
                     IS the financing rate
Merger arb           ⚠️ NOT riskless — you are short the deal-break probability
Convertible arb      ⚠️ leveraged, and it failed spectacularly in 2008
Statistical arb      ⚠️ not arbitrage at all — a positive-expectancy bet
```
> **⚠️ GOTCHA — most "arbitrage opportunities" a retail participant sees are one of four
> things**: ⚠️ **stale data**, **a price you cannot actually transact at** (the quote
> disappears when you send the order), **a cost you haven't counted** (withdrawal fees,
> spreads, financing, tax), **or a genuine risk you haven't identified** (counterparty,
> settlement, or the asset not being fungible across venues).
> ⚠️ **If it looks riskless and it's still there, you are the one who hasn't found the
> risk.** **The crypto cross-exchange spread that persists is usually a withdrawal
> restriction or a solvency signal.**

---
