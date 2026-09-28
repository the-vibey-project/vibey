---
id: skill-12-vehicle-routing-the-core-problem-7dceb87c5c
purpose: 12 vehicle routing the core problem
source: src/vibey_tools/skills/plugins/logistics-software-optimization/skills/logistics-routing-packing-scheduling-and-network-design/SKILL.md
requires: ["skill-11-tsp-2318b51a3f"]
links: ["skill-13-packing-and-loading-2605610209"]
---

## §12. ⚠️ Vehicle Routing — The Core Problem

**⚠️ The variant alphabet, because the acronym tells you what you're dealing with:**
```
CVRP     capacitated
VRPTW    ⚠️ + time windows. THE most common real variant, and the tightest
         windows are where feasibility itself becomes hard
VRPPD    pickup and delivery (⚠️ + precedence and pairing constraints)
MDVRP    multi-depot
HFVRP    heterogeneous fleet
PVRP     periodic (multi-day patterns)
⚠️ SDVRP  split delivery — one customer served by multiple vehicles
DVRP     dynamic (§23)      SVRP  stochastic (§23)
⚠️ VRPB   backhauls
OVRP     open (vehicles don't return to depot — common with contractors)
```
**⚠️ The constraints that actually appear in real deployments, and which the textbook
formulations omit:**
```
⚠️ Driver hours, mandatory breaks, and legal duty limits (HOS/tachograph)
⚠️ Skills and certifications — who can service what
⚠️ Vehicle-site compatibility — height, weight, access restrictions
⚠️ Multiple capacity dimensions — weight AND volume AND pallet positions
⚠️ Loading sequence / LIFO — you can't unload what's behind something else (§13)
⚠️ Time-dependent travel times — rush hour is not a constant multiplier
⚠️ Customer preferences, standing appointments, "same driver" requirements
⚠️ Depot dock capacity and loading windows
⚠️ Multi-day / multi-trip — a vehicle returns and reloads
⚠️ Fairness across drivers — an equity objective nobody mentions until day one
```
> **⚠️ GOTCHA — driver hours-of-service rules are where naive VRP implementations break,
> and the failure is expensive rather than merely suboptimal.** ⚠️ **Break placement
> interacts with time windows non-trivially: a required break can push you past a window,
> and where you place the break changes which windows remain reachable.** **Bolting HOS on
> after the fact produces plans that are illegal to execute.** **Model it from the start.**

**⚠️ Practical architecture that works:**
```
1. ⚠️ CLUSTER FIRST, ROUTE SECOND for very large instances — geographic or
   capacity-based decomposition into tractable subproblems
2. ⚠️ Construct an initial solution (savings/Clarke-Wright, insertion)
3. ⚠️ ALNS to improve, with the time budget as the stopping rule (§8)
4. ⚠️ Post-process for the human requirements: stability vs yesterday,
   fairness, and any preference rules
5. ⚠️ Validate feasibility INDEPENDENTLY of the optimizer. A separate
   checker catches modeling bugs the optimizer will happily exploit
```
**⚠️ Step 5 is not optional.** **An optimizer will find and exploit every gap in your
constraint model, and it will look like a great solution until a driver tries to run it.**

---
