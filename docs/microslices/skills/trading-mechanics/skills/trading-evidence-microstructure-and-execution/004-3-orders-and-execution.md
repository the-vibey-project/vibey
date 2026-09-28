---
id: skill-3-orders-and-execution-5496ed9e8c
purpose: 3 orders and execution
source: src/vibey_tools/skills/plugins/trading-mechanics/skills/trading-evidence-microstructure-and-execution/SKILL.md
requires: ["skill-2-market-microstructure-b495fd3d10"]
links: []
---

## §3. Orders and Execution

```
MARKET      ⚠️ guarantees execution, NOT price. Dangerous in thin markets or at the open
LIMIT       ⚠️ guarantees price, NOT execution. The default for anything not urgent
STOP        becomes a market order at the trigger — ⚠️ so it does NOT guarantee your price
STOP-LIMIT  ⚠️ may not fill at all, which in a fast move is the failure you didn't want
TRAILING STOP · IOC / FOK · MOC / LOC · ICEBERG
```
> **⚠️ GOTCHA — a stop-loss is not a loss limit.** ⚠️ **It triggers a market order, and in
> a gap or a fast move you fill far below it.** **Overnight gaps, halts and news events
> routinely blow through stops.** **"I had a stop at 5% so my risk was 5%" is false, and
> people learn this expensively.**

**Slippage** — the difference between expected and realized price. **Market impact** — your
own order moving the price, ⚠️ **which scales roughly with the square root of order size
relative to volume.** **Execution algorithms** (VWAP, TWAP, POV, implementation shortfall)
exist because of this.
**⚠️ Liquidity is not constant**: it evaporates exactly when you most want it, and
⚠️ **wide spreads at the open and close of illiquid names are where retail orders get
harvested.**
