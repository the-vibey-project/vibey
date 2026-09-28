---
id: skill-7-metaheuristics-e8b810036e
purpose: 7 metaheuristics
source: src/vibey_tools/skills/plugins/logistics-software-optimization/skills/logistics-constraint-programming-metaheuristics-and-bounds/SKILL.md
requires: ["skill-6-constraint-programming-b804171bbf"]
links: ["skill-8-local-search-and-large-neighbourhood-search-a02e0a3637"]
---

## §7. Metaheuristics

**⚠️ When exact methods don't fit the time budget. All of them are variations on "search
the neighbourhood, sometimes accept worse, escape local optima."**
```
LOCAL SEARCH / HILL CLIMBING   ⚠️ the base. Gets stuck
SIMULATED ANNEALING            accept worse with decreasing probability
TABU SEARCH                    ⚠️ forbid recent moves to escape cycles.
                               Historically very strong on VRP
GENETIC / EVOLUTIONARY         ⚠️ popular, and frequently OUTPERFORMED by
                               simpler LNS on routing. Popularity ≠ performance
ANT COLONY, PARTICLE SWARM     ⚠️ heavily published, rarely the best choice
   in production. Be sceptical of the metaphor-driven literature here
GRASP, VNS, ⚠️ LNS/ALNS        §8 — the ones that actually win
HYPER-HEURISTICS               choose among heuristics adaptively
```
> **⚠️ GOTCHA — the metaheuristic literature has a serious novelty problem.** ⚠️ **A large
> body of published "novel" nature-inspired metaheuristics (harmony search, various animal
> algorithms) has been criticized as rebranding existing methods with new metaphors, and
> comparisons are frequently against weak baselines on synthetic instances.** **This is a
> well-documented critique within the OR community.** **⚠️ For routing, start with LNS —
> it is the practical state of the art and it is simple.**

---
