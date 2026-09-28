---
id: skill-5-derivatives-de182a778a
purpose: 5 derivatives
source: src/vibey_tools/skills/plugins/trading-mechanics/skills/trading-asset-classes-derivatives-and-analysis/SKILL.md
requires: ["skill-4-asset-classes-ffb19cd6d5"]
links: ["skill-6-technical-analysis-honestly-939d5be590"]
---

## §5. Derivatives

**Futures** — ⚠️ **standardized, exchange-traded, daily mark-to-market with margin calls.**
**Leverage is embedded and large.** **Contango/backwardation and roll.**
**Options**:
```
Call / put · long / short · strike · expiry · American / European
Intrinsic + extrinsic value
GREEKS ⚠️
  Delta  sensitivity to underlying
  Gamma  ⚠️ rate of change of delta — why short options positions blow up suddenly
  Theta  ⚠️ time decay, and it ACCELERATES near expiry
  Vega   sensitivity to implied volatility
  Rho    interest rates
```
**⚠️ Black-Scholes assumes constant volatility, which is false** — ⚠️ **the volatility
smile/skew is the market's correction, and it exists because the model's assumption
doesn't hold.**
> **⚠️ GOTCHA — long options lose money by default, and short options have unbounded
> risk.** ⚠️ **Buying options means you need the move to happen, in your direction, before
> expiry, by more than the premium plus decay — three conditions, and theta works against
> you every day.** **Selling options inverts it: you win small amounts frequently and lose
> catastrophically rarely.** ⚠️ **A short-volatility strategy will show an excellent track
> record right up until it doesn't, and the loss distribution means historical returns
> systematically overstate its quality.**

**⚠️ Implied vs realized volatility is the actual trade in most options positions**, not
direction. **Selling options is structurally short volatility; there is a documented
volatility risk premium, which is compensation for bearing exactly that tail risk.**
**Swaps and CFDs** — ⚠️ **CFDs are banned for US retail, heavily restricted in the EU/UK,
and the broker disclosures required in those jurisdictions are themselves data on
outcomes** (§1 → `trading-evidence-microstructure-and-execution`).

---
