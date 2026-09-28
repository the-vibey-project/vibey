---
id: skill-3-the-aggregation-traps-6b8b4375cd
purpose: 3 the aggregation traps
source: src/vibey_tools/skills/plugins/reporting-and-dashboards/skills/reporting-architecture-modelling-and-aggregation-traps/SKILL.md
requires: ["skill-2-dimensional-modelling-0fe3e94485"]
links: ["skill-4-metric-definition-pitfalls-c5891211cc"]
---

## §3. ⚠️ The Aggregation Traps

**⚠️ This section is the highest-value part of the document. These bugs return successful
queries with wrong numbers, and they are extremely common.**

### 3.1 Fan-out (the chasm trap)
> **⚠️ GOTCHA — joining a fact to a one-to-many relationship multiplies your measures.**
> ```
> orders (1 row, amount = $100)
>   JOIN order_items (3 rows)
>   → SUM(orders.amount) = $300     ⚠️ WRONG, and it looks fine
> ```
> ⚠️ **The join duplicated the order row three times, and the sum duplicated with it.**
> **This is the single most common cause of inflated revenue figures in BI**, and it is
> especially insidious because **the number is plausible — just too big.**
>
> **The fixes**: **aggregate before joining** (⚠️ **the cleanest**), use
> `SUM(DISTINCT ...)` carefully, use window functions, ⚠️ **or let a semantic layer handle
> it — Looker's `symmetric aggregates` and MetricFlow's join logic exist specifically for
> this** (§5 → `reporting-semantic-layer-time-and-performance`).

### 3.2 The chasm trap proper
**⚠️ Two fact tables joined through a shared dimension produce a Cartesian product.**
```
customers ← orders  (3 orders)
customers ← support_tickets (4 tickets)
JOIN both through customers → ⚠️ 12 rows. Both sums are wrong
```
**⚠️ The fix is never a join**: aggregate each fact separately and combine the results —
**a `FULL OUTER JOIN` on the aggregates, or a union-and-pivot pattern.**

### 3.3 Additivity
```
FULLY ADDITIVE      revenue, units — ⚠️ sum across every dimension including time
SEMI-ADDITIVE       ⚠️ balances, inventory, headcount — additive across everything
                    EXCEPT time. Summing December's daily balances is nonsense;
                    you want the last value, or an average
NON-ADDITIVE        ⚠️ ratios, percentages, averages, distinct counts.
                    NEVER sum, and never average
```
> **⚠️ GOTCHA — the most common non-additive error is averaging a ratio.**
> **Conversion rate for three regions: 10%, 20%, 30%. The company rate is NOT 20%.**
> ⚠️ **You must recompute from the components: `SUM(conversions)/SUM(visits)`.**
> **The average-of-averages answer is wrong whenever the denominators differ, which is
> essentially always.**

### 3.4 ⚠️ Distinct counts don't decompose
**`COUNT(DISTINCT user)` per region does not sum to `COUNT(DISTINCT user)` overall** —
⚠️ **a user active in two regions is counted twice.** **This breaks pre-aggregation,
breaks roll-ups, and breaks any cached daily table you were hoping to sum into a monthly
figure.**
**⚠️ The mitigations**: recompute at each grain (expensive but correct), or use
**HyperLogLog sketches**, which ⚠️ **are mergeable and approximate — and the approximation
is usually fine for a dashboard and not fine for billing.**

---
