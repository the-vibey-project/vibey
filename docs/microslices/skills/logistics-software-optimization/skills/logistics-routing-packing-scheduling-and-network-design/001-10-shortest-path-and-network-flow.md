---
id: skill-10-shortest-path-and-network-flow-8893b5918a
purpose: 10 shortest path and network flow
source: src/vibey_tools/skills/plugins/logistics-software-optimization/skills/logistics-routing-packing-scheduling-and-network-design/SKILL.md
requires: []
links: ["skill-11-tsp-2318b51a3f"]
---

## §10. Shortest Path and Network Flow

**⚠️ The tractable core. These are in P, and they're the primitives everything else calls.**
```
Dijkstra          ⚠️ non-negative weights. O((V+E) log V) with a heap
Bellman-Ford      handles negative weights; detects negative cycles
A*                ⚠️ Dijkstra + admissible heuristic. Needs a heuristic that
                  never overestimates, or you lose optimality
⚠️ CONTRACTION HIERARCHIES / CH  the reason your map app answers instantly.
   Heavy preprocessing, microsecond queries on continental road networks
Floyd-Warshall    ⚠️ all-pairs, O(V³) — fine for small graphs, hopeless for road nets
MIN COST FLOW     ⚠️ hugely underused. Transportation, transshipment,
   assignment and many balancing problems are all min-cost-flow in disguise
MAX FLOW / MIN CUT   capacity analysis, bottleneck identification
```
**⚠️ Recognizing a network flow problem is a genuine superpower**: ⚠️ **if you can model it
as min-cost flow, it solves in polynomial time with integral solutions guaranteed —
no MIP needed, no gap, no time limit.** **Many people build a MIP for a problem that was
secretly a flow.**

---
