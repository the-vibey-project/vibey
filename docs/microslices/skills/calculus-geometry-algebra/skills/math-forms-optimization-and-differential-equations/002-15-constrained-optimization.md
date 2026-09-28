---
id: skill-15-constrained-optimization-b8623736d5
purpose: 15 constrained optimization
source: src/vibey_tools/skills/plugins/calculus-geometry-algebra/skills/math-forms-optimization-and-differential-equations/SKILL.md
requires: ["skill-14-differential-forms-9e8062eada"]
links: ["skill-16-differential-equations-b484159deb"]
---

## §15. Constrained Optimization

**Lagrange multipliers** — to optimize `f` subject to `g = 0`:
```
∇f = λ∇g
```
**⚠️ The geometric reason, which makes it memorable**: at a constrained optimum, **the level
set of `f` is tangent to the constraint surface**, so their gradients are parallel (§12 → `math-calculus-and-vector-calculus`).
**If they weren't, you could move along the constraint and improve.**
**⚠️ `λ` is the shadow price — the rate of change of the optimum with respect to relaxing
the constraint. That interpretation is often the most useful output.**

**KKT conditions** extend this to inequality constraints:
```
Stationarity · Primal feasibility · Dual feasibility (μ ≥ 0)
⚠️ Complementary slackness: μᵢgᵢ = 0 — either the constraint is active or its
   multiplier is zero
```
**⚠️ KKT is necessary under constraint qualification, and sufficient for convex problems**
— **which is why convexity matters so much: it converts a necessary condition into a
certificate of global optimality.**
**Duality** — the dual gives a bound; ⚠️ **strong duality (zero gap) holds for convex
problems under Slater's condition.**

---
