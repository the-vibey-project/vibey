---
id: skill-17-inventory-d3f15f7bcc
purpose: 17 inventory
source: src/vibey_tools/skills/plugins/logistics-software-optimization/skills/logistics-inventory-forecasting-operations-and-solvers/SKILL.md
requires: []
links: ["skill-18-forecasting-b865482847"]
---

## §17. Inventory

```
EOQ            ⚠️ the classic square-root formula. Assumptions rarely hold,
   and it's still a useful order-of-magnitude sanity check
⚠️ NEWSVENDOR  single period, stochastic demand. Optimal service level =
   Cu / (Cu + Co) — underage cost over total. ⚠️ THE key insight: your
   service level should follow from the COST ASYMMETRY, not from a target
   somebody picked
(s,S) / (R,Q)  reorder point policies
SAFETY STOCK   ⚠️ ≈ z · σ_demand-over-lead-time. Note it scales with the
   square root of lead time — ⚠️ so REDUCING LEAD TIME VARIABILITY beats
   reducing average lead time, usually by a lot
MULTI-ECHELON  ⚠️ where to hold stock across a network. Risk pooling:
   consolidated inventory needs less safety stock for the same service
   level, scaling with √n
ABC / XYZ      segmentation by value and by variability
```
> **⚠️ GOTCHA — the bullwhip effect is a structural property, not a forecasting failure.**
> ⚠️ **Demand variability amplifies up the supply chain because of order batching, lead
> time, price promotions and rationing behaviour** — **it arises from the STRUCTURE even
> with rational actors.** **You mitigate it with information sharing and shorter lead
> times, not with better local forecasts.**

---
