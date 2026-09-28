---
id: skill-20-warehouse-operations-0caaec109d
purpose: 20 warehouse operations
source: src/vibey_tools/skills/plugins/logistics-software-optimization/skills/logistics-inventory-forecasting-operations-and-solvers/SKILL.md
requires: ["skill-19-the-landscape-0cc4cb5c6a"]
links: ["skill-21-last-mile-828124ef3f"]
---

## §20. Warehouse Operations

**⚠️ Travel time dominates manual picking** — **commonly cited as roughly half of picker
time** — **so most warehouse optimization is really travel reduction.**
```
SLOTTING       ⚠️ put fast movers near dispatch; account for ergonomics
               (golden zone) and for affinity (items ordered together)
PICK PATH      ⚠️ TSP on the warehouse graph. S-shape and return heuristics
               are common and near-optimal for simple layouts
BATCHING       ⚠️ pick multiple orders per trip — usually the single biggest
               travel win available
ZONING         pick-and-pass vs pick-and-sort
WAVE vs WAVELESS  ⚠️ batched release vs continuous flow
GOODS-TO-PERSON   ⚠️ AS/RS, shuttles, AMRs — inverts the problem: now you
               optimize robot fleet movement and storage assignment instead
```
**⚠️ Labour standards and ergonomics are constraints, not preferences** — **and an
optimizer that maximizes picks per hour without them produces injury rates and turnover
that cost more than the throughput gained.**

---
