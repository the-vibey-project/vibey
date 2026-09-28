---
id: skill-14-costs-and-frictions-9abd953352
purpose: 14 costs and frictions
source: src/vibey_tools/skills/plugins/trading-mechanics/skills/trading-risk-costs-backtesting-and-psychology/SKILL.md
requires: ["skill-13-risk-and-position-sizing-7c13453806"]
links: ["skill-15-backtesting-pitfalls-a65e638125"]
---

## §14. Costs and Frictions

```
Commissions      ⚠️ often zero on US equities — the cost moved elsewhere (§2)
Spread           ⚠️ paid on EVERY round trip, and it is the dominant cost for
                 frequent traders
Slippage         §3
Market impact    §3
Financing        margin interest, overnight swap, futures roll
Borrow fees      short selling — ⚠️ can be enormous on hard-to-borrow names
Taxes            §17 — ⚠️ short-term gains are typically taxed less favourably
Data and tools   real cost, frequently ignored in profitability calculations
⚠️ OPPORTUNITY COST  the time, and the return you'd have earned passively
```
**⚠️ The arithmetic that decides it**: **round-trip cost × trades per year, against your
edge per trade.** ⚠️ **A 0.1% round-trip cost with 500 trades a year consumes 50% of
capital in costs alone.** **You need an edge exceeding that before you have earned
anything, and that is why frequency is the enemy** (§1 → `trading-evidence-microstructure-and-execution`).

---
