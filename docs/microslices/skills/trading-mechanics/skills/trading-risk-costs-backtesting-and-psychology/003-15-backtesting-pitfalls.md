---
id: skill-15-backtesting-pitfalls-a65e638125
purpose: 15 backtesting pitfalls
source: src/vibey_tools/skills/plugins/trading-mechanics/skills/trading-risk-costs-backtesting-and-psychology/SKILL.md
requires: ["skill-14-costs-and-frictions-9abd953352"]
links: ["skill-16-psychology-and-harm-ca059d859f"]
---

## §15. Backtesting Pitfalls

**⚠️ A backtest is a hypothesis, not evidence, and almost every appealing backtest is
wrong for one of these reasons:**
```
LOOK-AHEAD BIAS      ⚠️ using data unavailable at the time — restated fundamentals,
                     index membership known in advance, closing prices to trade the close
SURVIVORSHIP BIAS    ⚠️ delisted and bankrupt companies missing from your universe
OVERFITTING          ⚠️ testing enough variants guarantees one looks good by chance
DATA SNOOPING        ⚠️ the whole community mining the same dataset — even honest
                     out-of-sample tests are contaminated
IGNORING COSTS       ⚠️ §14 — the most common single reason a strategy dies live
IGNORING CAPACITY    it worked on $10k and moves the market at $10M
REGIME DEPENDENCE    ⚠️ a strategy tested only in a bull market
```
**⚠️ Practices that help**: **out-of-sample and walk-forward testing, holding out data you
genuinely never look at, penalizing parameter count, paper trading before capital,
and — the discipline almost nobody keeps — counting every strategy you tested, because
the tenth variant looking good is expected by chance.**
⚠️ **If a backtest shows a Sharpe of 3, the prior should be that you have made a mistake,
and it is usually look-ahead bias.**

---
