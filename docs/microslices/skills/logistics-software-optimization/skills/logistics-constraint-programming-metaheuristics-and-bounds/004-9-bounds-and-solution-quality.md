---
id: skill-9-bounds-and-solution-quality-ebcd3c5c49
purpose: 9 bounds and solution quality
source: src/vibey_tools/skills/plugins/logistics-software-optimization/skills/logistics-constraint-programming-metaheuristics-and-bounds/SKILL.md
requires: ["skill-8-local-search-and-large-neighbourhood-search-a02e0a3637"]
links: []
---

## §9. Bounds and Solution Quality

> **⚠️ GOTCHA — without a bound you have no idea whether your heuristic is 2% or 40% from
> optimal, and "it produced a solution" tells you nothing.** ⚠️ **This is the single most
> common gap in home-grown optimizers.**

**⚠️ How to get a bound**: **the LP relaxation; a Lagrangian relaxation; a simplified
problem (e.g. the assignment relaxation of a TSP); or a column-generation lower bound.**
**⚠️ Even a crude bound is transformative** — **it converts "the heuristic ran" into "we
are within X%," which is the number that justifies further investment or closes the
project.**
**⚠️ Benchmark against standard instance libraries**: **TSPLIB, CVRPLIB / Solomon and
Gehring-Homberger for VRPTW, MIPLIB for MIP.** ⚠️ **And benchmark against the HUMAN
baseline too, because that's the actual decision.**

---

# PART II — THE CORE PROBLEM FAMILY
