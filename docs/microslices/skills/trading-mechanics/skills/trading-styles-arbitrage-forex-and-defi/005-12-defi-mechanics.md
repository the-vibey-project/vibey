---
id: skill-12-defi-mechanics-7c1a4d91af
purpose: 12 defi mechanics
source: src/vibey_tools/skills/plugins/trading-mechanics/skills/trading-styles-arbitrage-forex-and-defi/SKILL.md
requires: ["skill-11-forex-acf0791b23"]
links: []
---

## §12. DeFi Mechanics

**⚠️ The mechanics are genuinely interesting engineering. The risk profile is severe and
different in kind from traditional markets.**

**AMMs** replace the order book with a formula. **Constant product: `x · y = k`.** ⚠️ **The
pool always quotes a price and always has liquidity — that's the innovation — and it
prices purely off its own reserves, so it needs arbitrageurs to track the outside market.**
**Concentrated liquidity (Uniswap V3)** lets LPs specify a price range, ⚠️ **improving
capital efficiency and adding active management burden.**

**⚠️ Impermanent loss — the most misunderstood concept in DeFi:**
> **⚠️ GOTCHA — impermanent loss is not a fee or a bug. It is the arbitrageur's profit,
> paid by you.** ⚠️ **When the external price moves, arbitrageurs buy the underpriced side
> of your pool and sell the overpriced side until the pool matches the market. That
> difference is extracted from the LP.**
> **The mechanical result: you always end up with more of the asset that fell and less of
> the one that rose.** ⚠️ **If ETH rises 50%, an ETH/stablecoin LP position is worth more
> than at deposit but meaningfully less than simply holding** — **a worked example puts
> it around 5.7% below holding for a 50% move.**
> ⚠️ **"Impermanent" assumed prices revert. They frequently don't, and the loss
> crystallizes on withdrawal.** **The academic literature has largely moved to
> loss-versus-rebalancing (LVR), which measures adverse selection against continuous
> rebalancing and — unlike IL — is monotonically increasing and path-dependent.**
> ⚠️ **LVR is the more honest measure, and it is worse than IL suggests.**

**⚠️ Fees can offset IL, and whether they do is an empirical question per pool** —
**high-volume, low-volatility pairs are where the arithmetic works; volatile pairs in
trending markets are where it doesn't.**

**MEV** — ⚠️ **value extracted by reordering, inserting or censoring transactions in a
block.** **Sandwich attacks (front-run your swap, back-run it), liquidation racing,
arbitrage.** ⚠️ **Empirical work shows MEV amplifies LP losses beyond what IL alone
predicts.** **Mitigations: private mempools, intent-based systems where solvers compete to
fill your order (CoW Swap, UniswapX), slippage limits.**

**Lending protocols** — ⚠️ **over-collateralized by necessity, because there is no recourse
and no identity.** **Liquidation when the health factor breaches; liquidators are
incentivized with a bonus.** ⚠️ **Cascading liquidations in a sharp move are a documented
systemic pattern.**
**Oracles** — ⚠️ **smart contracts cannot see external prices, so oracles bridge that gap
and are therefore the attack surface.** **Oracle manipulation caused $403.2 million in
losses in 2022 alone.** **TWAP oracles reduce manipulation risk and add lag.**

**⚠️ Risks with no traditional-market analogue**: **smart contract bugs (immutable and
often unrecoverable), admin key and governance risk, bridge exploits, rug pulls, protocol
insolvency, and total loss of self-custodied keys.** ⚠️ **There is no deposit insurance,
no chargeback, and frequently no legal recourse.** **"Audited" reduces risk; it does not
eliminate it, and audited protocols have failed.**
