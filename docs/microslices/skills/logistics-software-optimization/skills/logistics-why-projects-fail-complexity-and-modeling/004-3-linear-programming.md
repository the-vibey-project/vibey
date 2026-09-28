---
id: skill-3-linear-programming-6ab356db91
purpose: 3 linear programming
source: src/vibey_tools/skills/plugins/logistics-software-optimization/skills/logistics-why-projects-fail-complexity-and-modeling/SKILL.md
requires: ["skill-2-complexity-honestly-fcb56ba9f5"]
links: ["skill-4-mip-and-branch-and-bound-31adb61761"]
---

## §3. Linear Programming

**⚠️ Continuous variables, linear objective and constraints. Polynomial-time solvable and
essentially a solved technology — LP is the workhorse underneath everything else.**
```
Simplex     ⚠️ exponential worst case, excellent in practice; warm-starts well
Interior point  polynomial; better on very large sparse problems
⚠️ DUALITY  every LP has a dual. Dual values = SHADOW PRICES — the marginal
   value of relaxing a constraint by one unit
```
**⚠️ Shadow prices are the most under-used output in applied optimization.** **They tell
you what to change about the BUSINESS, not just the plan:** ⚠️ **"the capacity constraint
at depot 3 has a shadow price of $400/unit" is an investment case, and it falls out of the
solve for free.**
**⚠️ Sensitivity analysis matters more than the optimal solution in planning contexts** —
**how much can a cost change before the plan changes?**

---
