---
id: skill-4-mip-and-branch-and-bound-31adb61761
purpose: 4 mip and branch and bound
source: src/vibey_tools/skills/plugins/logistics-software-optimization/skills/logistics-why-projects-fail-complexity-and-modeling/SKILL.md
requires: ["skill-3-linear-programming-6ab356db91"]
links: ["skill-5-modeling-well-6c1bfe7627"]
---

## §4. MIP and Branch-and-Bound

**⚠️ Add integrality and you leave P.** **Nearly every logistics decision is integer:
which vehicle, whether to open a facility, which order goes where.**
```
⚠️ BRANCH AND BOUND
  Solve the LP relaxation → a BOUND on the best possible
  Branch on a fractional variable → two subproblems
  PRUNE any subproblem whose bound is worse than the incumbent
⚠️ CUTTING PLANES  add valid inequalities to tighten the relaxation
BRANCH AND CUT     ⚠️ both. What every modern solver does
⚠️ PRESOLVE        eliminate variables and constraints before solving.
   Often the single largest speedup, and it's automatic
COLUMN GENERATION / BRANCH AND PRICE  ⚠️ for problems with enormous variable
   counts — generate columns (e.g. whole routes) as needed. THE technique
   behind exact VRP and crew scheduling methods
```
**⚠️ The MIP gap is the number you actually operate on**: **(incumbent − bound) /
incumbent.** ⚠️ **A 2% gap means you're provably within 2% of optimal — usually far more
than good enough, and often reached in seconds while proving optimality would take
hours.** **Set a gap tolerance and a time limit. Always.**

---
