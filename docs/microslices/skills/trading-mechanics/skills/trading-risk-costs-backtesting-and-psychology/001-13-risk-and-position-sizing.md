---
id: skill-13-risk-and-position-sizing-7c13453806
purpose: 13 risk and position sizing
source: src/vibey_tools/skills/plugins/trading-mechanics/skills/trading-risk-costs-backtesting-and-psychology/SKILL.md
requires: []
links: ["skill-14-costs-and-frictions-9abd953352"]
---

## §13. Risk and Position Sizing

**⚠️ This is the section that determines whether you survive long enough for an edge to
matter.**
```
Risk per trade   ⚠️ commonly 0.5–2% of capital. Position size = risk budget ÷ stop distance
Kelly criterion  f* = (bp − q)/b   ⚠️ optimal GROWTH, and full Kelly is far too
                 volatile in practice — fractional Kelly (¼ to ½) is standard
R-multiples      express results in units of initial risk
Correlation      ⚠️ ten positions in one sector is ONE position
Drawdown math    ⚠️ −50% requires +100% to recover. This asymmetry is the whole argument
                 for capping losses
```
> **⚠️ GOTCHA — leverage does not amplify returns; it amplifies returns and brings
> forward ruin.** ⚠️ **With enough leverage, a sequence of losses that would be survivable
> becomes terminal, and markets produce such sequences routinely.** **Risk of ruin rises
> nonlinearly with position size, and the point at which it becomes near-certain arrives
> earlier than intuition suggests.**
>
> ⚠️ **Never risk money you need.** **Rent, tuition, and emergency reserves have no place
> in a trading account, and this is not moralizing — it is that being forced to liquidate
> at a bad moment converts a temporary drawdown into a permanent loss.**

**⚠️ Path dependence is the underrated point**: **the same set of trades in a different
order can leave you fine or bankrupt.** **Expected value says nothing about survival.**
**⚠️ Ergodicity**: **time-average and ensemble-average returns differ under multiplicative
dynamics** — **which is the formal statement of why a positive expected return can still
ruin you.**

---
