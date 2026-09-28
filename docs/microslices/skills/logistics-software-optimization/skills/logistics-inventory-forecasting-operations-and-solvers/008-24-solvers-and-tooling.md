---
id: skill-24-solvers-and-tooling-4da5bc1f83
purpose: 24 solvers and tooling
source: src/vibey_tools/skills/plugins/logistics-software-optimization/skills/logistics-inventory-forecasting-operations-and-solvers/SKILL.md
requires: ["skill-23-dynamic-and-stochastic-605f48defd"]
links: []
---

## §24. Solvers and Tooling

```
COMMERCIAL MIP   ⚠️ Gurobi · IBM CPLEX · FICO Xpress · COPT (§25.1)
OPEN SOURCE MIP  ⚠️ HiGHS (the current default) · SCIP (excellent, check
                 licence terms) · CBC (older, slower)
CP               ⚠️ OR-Tools CP-SAT (outstanding, free) · IBM CP Optimizer
ROUTING          ⚠️ OR-Tools routing library · VROOM (open source, fast) ·
                 jsprit · commercial routing engines
MODELING LAYERS  ⚠️ Pyomo · PuLP · JuMP (Julia) · AMPL/GAMS · linopy
ROAD ROUTING     ⚠️ OSRM · Valhalla · GraphHopper (self-host; §22)
FIRST-ORDER/GPU  ⚠️ PDLP and cuPDLP — GPU LP for very large instances (§25.1)
```
**⚠️ Sensible defaults for a team starting out**: **OR-Tools for routing and scheduling
(free, well-documented, genuinely good); HiGHS for LP/MIP; a self-hosted OSRM for
distances; Pyomo or JuMP if you want solver portability.** ⚠️ **Buy a commercial MIP
licence when you have demonstrated that solve time is your binding constraint — and not
before, because §1 → `logistics-why-projects-fail-complexity-and-modeling` says it usually isn't.**
