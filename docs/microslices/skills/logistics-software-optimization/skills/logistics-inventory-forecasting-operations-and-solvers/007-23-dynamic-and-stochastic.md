---
id: skill-23-dynamic-and-stochastic-605f48defd
purpose: 23 dynamic and stochastic
source: src/vibey_tools/skills/plugins/logistics-software-optimization/skills/logistics-inventory-forecasting-operations-and-solvers/SKILL.md
requires: ["skill-22-data-9c3c95ab9b"]
links: ["skill-24-solvers-and-tooling-4da5bc1f83"]
---

## §23. Dynamic and Stochastic

**⚠️ Real logistics is not a static problem solved once.**
```
DYNAMIC       ⚠️ orders arrive during execution; vehicles are en route
STOCHASTIC    ⚠️ travel times, service times and demand are random variables
ONLINE        ⚠️ decide without knowing the future. Competitive ratio analysis
ROLLING HORIZON  ⚠️ re-optimize periodically over a moving window. THE
   standard practical approach
```
**Techniques**: **rolling-horizon re-optimization; scenario-based stochastic programming;
sample average approximation; robust optimization (⚠️ optimize the worst case — often too
conservative for logistics); chance constraints; and reinforcement learning
(⚠️ genuinely promising for dispatch-style sequential decisions, and much harder to
validate and deploy than the literature implies).**
**⚠️ The practical patterns that matter more than the theory:**
- ⚠️ **Buffer time in the plan.** **A plan with zero slack fails on the first delay and
  cascades.**
- ⚠️ **Re-optimize on a schedule AND on trigger events**, **not continuously — continuous
  re-optimization destabilizes the plan** (§1 → `logistics-why-projects-fail-complexity-and-modeling`).
- ⚠️ **Freeze a near horizon.** **Don't change what a driver is doing in the next 30
  minutes.** **This is both operationally necessary and a large search-space reduction.**
- **Anticipate rather than react where you can** — **positioning idle capacity toward
  expected demand.**

---
