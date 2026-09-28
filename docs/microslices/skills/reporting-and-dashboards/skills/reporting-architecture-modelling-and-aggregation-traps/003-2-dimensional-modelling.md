---
id: skill-2-dimensional-modelling-0fe3e94485
purpose: 2 dimensional modelling
source: src/vibey_tools/skills/plugins/reporting-and-dashboards/skills/reporting-architecture-modelling-and-aggregation-traps/SKILL.md
requires: ["skill-1-the-architecture-ea924d1aca"]
links: ["skill-3-the-aggregation-traps-6b8b4375cd"]
---

## §2. Dimensional Modelling

**⚠️ Kimball's star schema is 1996 and still correct, because it solves a problem that
hasn't changed: making a warehouse queryable by people who didn't build it.**

```
FACT table       ⚠️ measurements at a defined GRAIN, plus foreign keys
DIMENSION tables descriptive attributes you filter and group by
```
> **⚠️ GOTCHA — declaring the grain is the single most important modelling decision, and
> skipping it causes most fact-table bugs.** ⚠️ **"One row per order line per shipment" is
> a grain; "orders" is not.** **Every measure in the table must be true at that grain.**
> **If you find yourself unsure whether to sum a column, the grain was never properly
> declared.**

**Fact types, and the distinction drives everything downstream:**
```
Transaction     one row per event. ⚠️ Fully additive
Periodic snapshot  state at intervals (daily balance). ⚠️ NOT additive over time
Accumulating snapshot  one row per process instance, updated as it progresses
Factless        ⚠️ events with no measure — attendance, eligibility. Count the rows
```

**Dimensions**: **conformed** (⚠️ **shared across facts — this is what makes cross-process
analysis possible, and it's the hard organizational part**), **degenerate** (an order
number living on the fact), **junk** (⚠️ **flags bundled together rather than exploding
your dimension count**), **role-playing** (⚠️ **one date dimension viewed as order date,
ship date, return date**).

**⚠️ Slowly changing dimensions — get this wrong and history silently rewrites itself:**
```
Type 1  overwrite       ⚠️ history LOST. Last year's report changes when someone
                        moves territory. Often not what anyone wanted
Type 2  new row + validity dates + current flag  ⚠️ the standard for real history
Type 3  previous-value column   limited
Type 4/6  hybrids
```
⚠️ **The symptom of an unintended Type 1 is a historical report that no longer reproduces
— and by the time someone notices, the old values are gone.**

**One Big Table (OBT)** — ⚠️ **denormalize everything into a wide table.** **Columnar
storage makes this cheap and it's genuinely simpler for consumers.** ⚠️ **The costs are
real though: update anomalies, storage, and the fan-out problem (§3) baked in
permanently rather than at query time.** **Use it for a well-understood consumption
surface, not as the modelling layer.**

---
