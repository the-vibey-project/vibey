---
id: skill-2-market-microstructure-b495fd3d10
purpose: 2 market microstructure
source: src/vibey_tools/skills/plugins/trading-mechanics/skills/trading-evidence-microstructure-and-execution/SKILL.md
requires: ["skill-1-what-the-evidence-actually-shows-dced0929c1"]
links: ["skill-3-orders-and-execution-5496ed9e8c"]
---

## §2. Market Microstructure

**⚠️ Understanding who you're trading against is prerequisite to any claim of edge.**

**The order book**: bids and asks, **the spread**, depth, **price-time priority** in most
lit venues.
**Participants**: **market makers** (⚠️ **quote both sides, earn the spread, and manage
inventory — they are paid to be your counterparty**), **HFT** (⚠️ **latency arbitrage,
microsecond horizons, colocated**), institutions (⚠️ **working large orders over hours or
days to minimize impact**), retail, and **hedgers.**

**⚠️ Adverse selection is the concept that explains market maker behaviour**: **a market
maker loses to informed traders and profits from uninformed ones, so the spread is
partly compensation for that risk.** ⚠️ **Which means: if your order is easy to fill, that
is information about your order.**

**⚠️ Payment for order flow (PFOF)**: **retail orders are routed to wholesalers who
internalize them.** ⚠️ **The trade is real in both directions — retail typically gets
price improvement versus the displayed quote, and the wholesaler is paying for the flow
because it is profitable to trade against, being uninformed.** **"Free" commissions are
paid for somewhere.**
**Dark pools**, **lit venues**, **fragmentation and the consolidated tape**, **auctions**
(⚠️ **open and close auctions concentrate enormous volume, and the close is often the most
liquid moment of the day**).

**⚠️ Latency reality**: **professional infrastructure operates in microseconds; a retail
order travels over the public internet in milliseconds.** ⚠️ **That is roughly a
thousand-fold difference, and any strategy whose edge depends on speed is not available
to you.**

---
