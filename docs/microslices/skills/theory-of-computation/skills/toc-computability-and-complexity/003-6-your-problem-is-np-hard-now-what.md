---
id: skill-6-your-problem-is-np-hard-now-what-26f15bc1fa
purpose: 6 your problem is np hard now what
source: src/vibey_tools/skills/plugins/theory-of-computation/skills/toc-computability-and-complexity/SKILL.md
requires: ["skill-5-complexity-classes-a018974ce3"]
links: ["skill-7-sat-smt-and-solvers-853b252172"]
---

## §6. Your Problem Is NP-Hard. Now What?

**[DURABLE] This is the section with the most direct daily value, and the one most
engineers get wrong in both directions** — either despairing, or not recognizing the
hardness at all and shipping something that falls over at scale.

### 6.1 Recognizing it

**The canonical problems worth knowing by sight**, because your problem is usually one of
them wearing a business costume:

| Problem | Shows up as |
|---|---|
| **SAT / 3-SAT** | Configuration, feature flags, dependency resolution |
| **Knapsack / Subset Sum** | Budget allocation, resource packing, cart optimization |
| **Bin Packing** | VM placement, container scheduling, shipping |
| **Graph Coloring** | Register allocation, scheduling with conflicts, frequency assignment |
| **TSP / Vehicle Routing** | Delivery, tool-path, sequencing anything |
| **Set Cover** | Minimum test suite, sensor placement, feature selection |
| **Clique / Independent Set** | Compatibility groups, conflict-free selection |
| **Scheduling with constraints** | Almost every scheduling problem you'll be handed |
| **Integer Programming** | ⚠️ **The general form of most of the above** |

**[DURABLE] The tell**: you're choosing a subset or an ordering, constraints interact, and
a greedy choice early can be shown to force a bad outcome later. **When a problem has that
shape, look for the reduction before you start optimizing.**

### 6.2 The escape hatches, in order of usefulness

```
1. IS THE INPUT SMALL?           n=20 exhaustive search is instant. Check first.
2. IS IT ACTUALLY THE HARD CASE? Real inputs are structured; §6.3
3. USE A SOLVER                  SAT/SMT/MIP/CP — §7. Often the right answer
4. APPROXIMATE                   Many NP-hard problems have provable ratio bounds
5. HEURISTIC                     Greedy, local search, simulated annealing, GA
6. FIXED-PARAMETER TRACTABLE     f(k)·poly(n) — exponential only in a small parameter
7. PSEUDO-POLYNOMIAL             Knapsack is O(nW) — fine if W is small
8. SPECIAL CASE                  Is your graph a tree? planar? bounded treewidth?
9. RELAX THE PROBLEM             ⚠️ Often the real answer: does the business need OPTIMAL?
10. CHANGE THE PROBLEM           Ditto
```

**[DURABLE] #9 and #10 deserve more attention than they get.** "Optimal" is usually a
requirement someone assumed rather than one the business stated. **A solution within 2% of
optimal, computed in 100 ms, beats an optimal one computed in six hours** for nearly every
real application — and asking that question is often worth more than any algorithm.

**Approximation with guarantees** is genuinely useful: Vertex Cover has a simple 2-approx;
Set Cover has a ln(n) approximation and **that's provably the best possible unless P = NP**;
Metric TSP has classical constant-factor results. **⚠️ Some problems are hard even to
approximate** — that's the PCP theorem's practical legacy, and it means "just approximate
it" is not always available.

### 6.3 The most important practical caveat

**[DURABLE] NP-hardness is a statement about worst-case inputs over all instances. It says
nothing about yours.**

Real instances have structure: dependency graphs are sparse and near-acyclic, schedules
have natural clustering, configuration constraints are mostly independent. **Modern SAT
solvers routinely handle industrial instances with millions of variables** (§7) — instances
that are formally NP-complete and empirically easy.

**⚠️ The failure mode in both directions:**
- **Giving up because it's NP-hard**, when a solver would have done it in a second.
- **Assuming it'll be fine because it worked in testing**, when your test data was
  structured and production data isn't. **The exponential is still there and it will find
  you.** Set timeouts, have a fallback, and monitor solve times.

---
