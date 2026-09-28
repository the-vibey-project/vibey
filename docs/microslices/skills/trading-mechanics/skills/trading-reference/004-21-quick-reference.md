---
id: skill-21-quick-reference-b72811d616
purpose: 21 quick reference
source: src/vibey_tools/skills/plugins/trading-mechanics/skills/trading-reference/SKILL.md
requires: ["skill-20-books-2946a03220"]
links: ["skill-22-method-0c1d23b8fa"]
---

## §21. Quick Reference

### 21.1 Questions to answer before trading anything
- [ ] ⚠️ **What is my edge, stated specifically — who is on the other side and why are they wrong?**
- [ ] Have I read §1 → `trading-evidence-microstructure-and-execution`'s evidence and does my plan explain why I'd be the exception?
- [ ] ⚠️ **Round-trip cost × expected trades per year — what does that consume?** (§14 → `trading-risk-costs-backtesting-and-psychology`)
- [ ] What is my risk per trade, and can I survive 20 consecutive losses? (§13 → `trading-risk-costs-backtesting-and-psychology`)
- [ ] ⚠️ **Is this money I can lose entirely without it changing my life?** (§13 → `trading-risk-costs-backtesting-and-psychology`)
- [ ] Am I measuring against buy-and-hold, net of costs, tax and my time? (§14 → `trading-risk-costs-backtesting-and-psychology`)
- [ ] If backtested — have I checked for look-ahead, survivorship and overfitting? (§15 → `trading-risk-costs-backtesting-and-psychology`)
- [ ] ⚠️ **What is my stop condition — the drawdown at which I stop, decided now?**
- [ ] Would I be comfortable showing a close friend my full P&L? (§16 → `trading-risk-costs-backtesting-and-psychology`)

### 21.2 Picker
| Question | Where |
|---|---|
| Should I expect to profit day trading? | ⚠️ **§1 → `trading-evidence-microstructure-and-execution`. The base rate is 97% losing** |
| Why did my stop fill so far below? | ⚠️ **Stops become market orders** (§3 → `trading-evidence-microstructure-and-execution`) |
| Why is my leveraged ETF underperforming? | Daily rebalancing decay (§4 → `trading-asset-classes-derivatives-and-analysis`) |
| Why is my option losing with the stock flat? | ⚠️ **Theta** (§5 → `trading-asset-classes-derivatives-and-analysis`) |
| Why did my LP position underperform holding? | ⚠️ **IL / LVR** (§12 → `trading-styles-arbitrage-forex-and-defi`) |
| Why did my backtest fail live? | ⚠️ **Costs, then look-ahead bias** (§14 → `trading-risk-costs-backtesting-and-psychology`, §15 → `trading-risk-costs-backtesting-and-psychology`) |
| How large should this position be? | ⚠️ **Risk budget ÷ stop distance; fractional Kelly** (§13 → `trading-risk-costs-backtesting-and-psychology`) |
| Is this arbitrage real? | ⚠️ **Find the risk you've missed** (§10 → `trading-styles-arbitrage-forex-and-defi`) |
| I'm trading to make back losses | ⚠️ **§16 → `trading-risk-costs-backtesting-and-psychology`. Stop and talk to someone** |

---
