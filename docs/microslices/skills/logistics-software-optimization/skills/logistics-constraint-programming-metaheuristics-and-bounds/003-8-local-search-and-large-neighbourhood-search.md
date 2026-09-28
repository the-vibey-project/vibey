---
id: skill-8-local-search-and-large-neighbourhood-search-a02e0a3637
purpose: 8 local search and large neighbourhood search
source: src/vibey_tools/skills/plugins/logistics-software-optimization/skills/logistics-constraint-programming-metaheuristics-and-bounds/SKILL.md
requires: ["skill-7-metaheuristics-e8b810036e"]
links: ["skill-9-bounds-and-solution-quality-ebcd3c5c49"]
---

## §8. ⚠️ Local Search and Large Neighbourhood Search

**⚠️ This is what actually powers production routing engines, and it's conceptually
simple.**
```
⚠️ LNS / ALNS (Adaptive LNS)
  1. Start from any feasible solution
  2. DESTROY — remove part of it (random stops, a geographic cluster,
     a whole route, the most "expensive" stops)
  3. REPAIR — reinsert greedily or with a small exact solve
  4. Accept or reject; ⚠️ ADAPT the weights on destroy/repair operators
     based on which have been working
  5. Repeat until the time budget is gone
```
**⚠️ Why it wins in practice:**
- ⚠️ **It handles arbitrary messy constraints.** **The repair step just has to respect
  them; you never need a clean mathematical formulation of every business rule.**
- ⚠️ **It's anytime.** **Stop whenever; you have a valid solution.** **This matches
  operational reality where you have 20 minutes, not "until optimal."**
- **⚠️ It warm-starts naturally**, **which is exactly what you need for §1 → `logistics-why-projects-fail-complexity-and-modeling`'s stability
  requirement and for §23 → `logistics-inventory-forecasting-operations-and-solvers`'s dynamic re-optimization.**
- **It parallelizes reasonably.**

**⚠️ Classic VRP local search moves worth knowing**: **2-opt and Or-opt (within a route),
relocate and swap (between routes), 2-opt* (cross-route tail exchange), and ⚠️ ejection
chains.** **Combined with LNS these cover most of what commercial engines do.**

---
