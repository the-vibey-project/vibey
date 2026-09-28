---
id: skill-2-complexity-honestly-fcb56ba9f5
purpose: 2 complexity honestly
source: src/vibey_tools/skills/plugins/logistics-software-optimization/skills/logistics-why-projects-fail-complexity-and-modeling/SKILL.md
requires: ["skill-1-why-optimization-projects-fail-2d0be2898b"]
links: ["skill-3-linear-programming-6ab356db91"]
---

## §2. Complexity, Honestly

```
P            solvable in polynomial time. ⚠️ Shortest path, LP, max flow,
             assignment, min spanning tree
NP-complete  ⚠️ decision problems where a solution is checkable fast
NP-hard      ⚠️ at least as hard. TSP, VRP, bin packing, most scheduling
```
> **⚠️ GOTCHA — "NP-hard" is routinely used to mean "impossible," and that is wrong in a
> way that matters commercially.** ⚠️ **It means no known algorithm guarantees optimality
> in polynomial time IN THE WORST CASE.** **It says nothing about your instances.**
> **⚠️ TSP instances with tens of thousands of cities have been solved to proven
> optimality; real VRPs with thousands of stops are routinely solved to within 1–3% of a
> lower bound in minutes.** **Structure in real data — geographic clustering, tight time
> windows, capacity limits — often makes practical instances far easier than the worst
> case.**
> **⚠️ The correct inference from NP-hardness is "don't expect a guaranteed-optimal exact
> method to scale," not "give up."**

**⚠️ What actually drives difficulty in practice** — **and it's rarely raw stop count:**
**the number of INTERACTING constraints; time window tightness (⚠️ tight windows can make
finding any feasible solution the hard part); heterogeneous fleets; and multi-objective
tradeoffs.** ⚠️ **A 500-stop problem with driver skills, time windows, capacity in three
dimensions, break rules and multi-day horizons is far harder than a 5,000-stop pure
capacitated VRP.**

---
