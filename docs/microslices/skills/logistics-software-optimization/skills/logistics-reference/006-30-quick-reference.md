---
id: skill-30-quick-reference-f7c9c240cd
purpose: 30 quick reference
source: src/vibey_tools/skills/plugins/logistics-software-optimization/skills/logistics-reference/SKILL.md
requires: ["skill-29-books-53af209527"]
links: ["skill-31-method-730408f990"]
---

## §30. Quick Reference

### 30.1 Picker
| Question | Answer |
|---|---|
| Where do I start on a new project? | ⚠️ **Profile the data. Not the model** (§1 → `logistics-why-projects-fail-complexity-and-modeling`) |
| Is my heuristic any good? | ⚠️ **Get a bound. Any bound** (§9 → `logistics-constraint-programming-metaheuristics-and-bounds`) |
| Solver says infeasible at 4am | ⚠️ **Soften constraints with penalties** (§5 → `logistics-why-projects-fail-complexity-and-modeling`) |
| Routing engine architecture? | ⚠️ **Cluster → construct → ALNS → post-process → validate** (§12 → `logistics-routing-packing-scheduling-and-network-design`) |
| Which metaheuristic? | ⚠️ **LNS/ALNS first** (§8 → `logistics-constraint-programming-metaheuristics-and-bounds`) |
| Is this actually a hard problem? | ⚠️ **Check whether it's min-cost flow** (§10 → `logistics-routing-packing-scheduling-and-network-design`) |
| Scheduling with resources and precedence? | ⚠️ **CP-SAT** (§6 → `logistics-constraint-programming-metaheuristics-and-bounds`, §15 → `logistics-routing-packing-scheduling-and-network-design`) |
| Distance matrix too slow/expensive? | ⚠️ **Self-host OSRM; k-nearest only** (§22 → `logistics-inventory-forecasting-operations-and-solvers`) |
| Plans keep running late | ⚠️ **Measure real service times; add buffer** (§21 → `logistics-inventory-forecasting-operations-and-solvers`, §23 → `logistics-inventory-forecasting-operations-and-solvers`) |
| Drivers reject the plan | ⚠️ **Stability penalty + an explainer** (§1 → `logistics-why-projects-fail-complexity-and-modeling`) |
| How much safety stock? | ⚠️ **Newsvendor on cost asymmetry, not a target SL** (§17 → `logistics-inventory-forecasting-operations-and-solvers`) |
| Which solver? | ⚠️ **OR-Tools + HiGHS until proven otherwise** (§24 → `logistics-inventory-forecasting-operations-and-solvers`) |
| Should we try quantum? | ⚠️ **No. Tune your LNS** (§25.2) |
| Can an LLM do this? | ⚠️ **As an interface and explainer, yes. As a solver, no** (§25.2) |

### 30.2 Before going live
- [ ] ⚠️ **Data profiled: address quality, service times, capacities, skills** (§22 → `logistics-inventory-forecasting-operations-and-solvers`)
- [ ] ⚠️ **Independent feasibility checker, separate from the optimizer** (§12 → `logistics-routing-packing-scheduling-and-network-design`)
- [ ] ⚠️ **A bound, so you can state solution quality** (§9 → `logistics-constraint-programming-metaheuristics-and-bounds`)
- [ ] Hard constraints limited to genuine impossibilities (§5 → `logistics-why-projects-fail-complexity-and-modeling`)
- [ ] ⚠️ **Stability penalty against the incumbent plan** (§1 → `logistics-why-projects-fail-complexity-and-modeling`)
- [ ] ⚠️ **Degraded fallback that always returns something** (§1 → `logistics-why-projects-fail-complexity-and-modeling`)
- [ ] Plan explainer: "why is this stop on this route?" (§1 → `logistics-why-projects-fail-complexity-and-modeling`)
- [ ] ⚠️ **Driver hours / breaks modeled, not bolted on** (§12 → `logistics-routing-packing-scheduling-and-network-design`)
- [ ] Runtime fits the operational window with margin (§1 → `logistics-why-projects-fail-complexity-and-modeling`)
- [ ] ⚠️ **Shadow-mode comparison against current human plans** (§1 → `logistics-why-projects-fail-complexity-and-modeling`)
- [ ] Penalty weights exposed as a business-facing interface (§5 → `logistics-why-projects-fail-complexity-and-modeling`)
- [ ] ⚠️ **Benchmarked on YOUR instances, not published rankings** (§25.1)

---
