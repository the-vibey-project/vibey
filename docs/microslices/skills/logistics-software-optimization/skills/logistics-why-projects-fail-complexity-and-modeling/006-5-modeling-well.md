---
id: skill-5-modeling-well-6c1bfe7627
purpose: 5 modeling well
source: src/vibey_tools/skills/plugins/logistics-software-optimization/skills/logistics-why-projects-fail-complexity-and-modeling/SKILL.md
requires: ["skill-4-mip-and-branch-and-bound-31adb61761"]
links: []
---

## §5. ⚠️ Modeling Well

**⚠️ The formulation matters more than the solver. A good model on a free solver beats a
bad model on an expensive one, routinely.**
```
⚠️ TIGHT vs LOOSE formulations. Two models with identical feasible integer
   sets can have vastly different LP relaxations. ⚠️ The tighter relaxation
   prunes far more and can be orders of magnitude faster
⚠️ BIG-M   the classic trap. M too large → weak relaxation, numerical
   instability, garbage. ⚠️ Use the SMALLEST valid M you can prove
⚠️ SYMMETRY  identical vehicles/machines mean the solver explores equivalent
   solutions repeatedly. Break it with ordering constraints
INDICATOR CONSTRAINTS  ⚠️ often better than big-M; solvers handle them natively
SOS constraints · piecewise linear via SOS2
⚠️ SOFT CONSTRAINTS  penalize in the objective rather than forbidding.
   ⚠️ THE most important practical modeling decision — see below
```
> **⚠️ GOTCHA — an infeasible model is useless to operations and "infeasible" is the worst
> possible output at 4am.** ⚠️ **Make almost everything soft with a penalty, ordered by
> business priority: hard constraints only for genuine physical or legal impossibilities.**
> **Then you always get a plan, and the violations are visible and ranked.**
> **⚠️ Bonus: penalty weights become the interface where operations expresses priorities,
> which converts an argument about the algorithm into a conversation about the business.**

**⚠️ Numerical hygiene** — **keep coefficient magnitudes within a few orders of magnitude
of each other; scale your data.** ⚠️ **Mixing costs in cents with distances in millimetres
produces coefficient ranges that make solvers behave erratically and unreproducibly.**
