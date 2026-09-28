---
id: skill-27-misconceptions-5ee43cf33f
purpose: 27 misconceptions
source: src/vibey_tools/skills/plugins/logistics-software-optimization/skills/logistics-reference/SKILL.md
requires: ["skill-26-anti-patterns-b8c3562f0a"]
links: ["skill-28-numbers-f2602bb9ec"]
---

## §27. Misconceptions

| Misconception | Correction |
|---|---|
| NP-hard means practically unsolvable | ⚠️ **Real instances solve to within a few % routinely** (§2 → `logistics-why-projects-fail-complexity-and-modeling`) |
| The algorithm is the hard part | ⚠️ **Data, hidden constraints and trust are** (§1 → `logistics-why-projects-fail-complexity-and-modeling`) |
| A better objective value is a better plan | ⚠️ **Not if operations won't run it** (§1 → `logistics-why-projects-fail-complexity-and-modeling`) |
| Stop count drives difficulty | ⚠️ **Interacting constraints and tight windows do** (§2 → `logistics-why-projects-fail-complexity-and-modeling`) |
| The solver choice matters most | ⚠️ **The formulation matters more** (§5 → `logistics-why-projects-fail-complexity-and-modeling`) |
| Make constraints hard so they're respected | ⚠️ **Soft + penalties; "infeasible" helps nobody** (§5 → `logistics-why-projects-fail-complexity-and-modeling`) |
| Genetic algorithms are state of the art for routing | ⚠️ **LNS/ALNS generally beats them** (§7 → `logistics-constraint-programming-metaheuristics-and-bounds`, §8 → `logistics-constraint-programming-metaheuristics-and-bounds`) |
| A heuristic that returns a solution is working | ⚠️ **Without a bound you know nothing** (§9 → `logistics-constraint-programming-metaheuristics-and-bounds`) |
| TSP is the hard part of routing | ⚠️ **Assignment to vehicles is** (§11 → `logistics-routing-packing-scheduling-and-network-design`, §12 → `logistics-routing-packing-scheduling-and-network-design`) |
| Straight-line distance is close enough | ⚠️ **Error is worst exactly where geography binds** (§22 → `logistics-inventory-forecasting-operations-and-solvers`) |
| Geocoding gives you a location | ⚠️ **It gives a point and a quality flag; the flag matters** (§22 → `logistics-inventory-forecasting-operations-and-solvers`) |
| Service time is roughly constant | ⚠️ **It varies hugely by stop type and destroys plans** (§21 → `logistics-inventory-forecasting-operations-and-solvers`) |
| Re-optimize continuously for best results | ⚠️ **It destabilizes the plan; freeze a near horizon** (§23 → `logistics-inventory-forecasting-operations-and-solvers`) |
| Safety stock should target a service level | ⚠️ **Newsvendor: derive it from cost asymmetry** (§17 → `logistics-inventory-forecasting-operations-and-solvers`) |
| Reduce average lead time | ⚠️ **Reducing lead time VARIABILITY usually matters more** (§17 → `logistics-inventory-forecasting-operations-and-solvers`) |
| Bullwhip is a forecasting failure | ⚠️ **It's structural** (§17 → `logistics-inventory-forecasting-operations-and-solvers`) |
| Fancy ML beats simple forecasting | ⚠️ **Often not, especially on intermittent demand** (§18 → `logistics-inventory-forecasting-operations-and-solvers`) |
| Open-source solvers are 100× slower | ⚠️ **Roughly 20×, and often fast enough** (§25.1) |
| Published solver benchmarks predict my performance | ⚠️ **Weakly. Benchmark your own models** (§25.1) |
| Quantum will solve routing soon | ⚠️ **Annealers cumbersome at a few hundred variables** (§25.2) |
| LLMs can solve optimization problems | ⚠️ **They're an interface to solvers, not a solver** (§25.2) |

---
