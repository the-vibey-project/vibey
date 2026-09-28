---
id: skill-12-multivariable-calculus-87d6860d6f
purpose: 12 multivariable calculus
source: src/vibey_tools/skills/plugins/calculus-geometry-algebra/skills/math-calculus-and-vector-calculus/SKILL.md
requires: ["skill-11-series-and-taylor-approximation-64c180bbe8"]
links: ["skill-13-vector-calculus-9e215a01b3"]
---

## §12. Multivariable Calculus

**Partial derivatives**, **gradient `∇f`** (⚠️ **direction of steepest ascent, and
perpendicular to level sets — the second fact is the one people forget and it's what
makes Lagrange multipliers work**), **directional derivative `∇f · û`**.

**Jacobian** `J` — ⚠️ **the matrix of the derivative as a linear map** (§9.2). **For
`f: ℝⁿ → ℝᵐ` it's `m×n`.** **The chain rule is matrix multiplication of Jacobians** —
⚠️ **which is exactly backpropagation.**

**Hessian** `H` — second partials, ⚠️ **symmetric when the function is `C²` (Clairaut),
which is why §6 → `math-inner-products-svd-and-numerical-reality`'s spectral theorem applies to it.**
```
H positive definite    ⚠️ local minimum
H negative definite    local maximum
H indefinite           ⚠️ saddle point
H singular             ⚠️ test inconclusive
```
**⚠️ In high dimensions, critical points of random functions are overwhelmingly saddles
rather than local minima** — the eigenvalues would all need the same sign by chance.
**This reframes what optimization is fighting.**

**Multiple integrals**, **Fubini** (⚠️ **exchange order of integration — requires
absolute integrability, and there are standard counterexamples when it fails**),
**change of variables with the Jacobian determinant** (§3 → `math-linear-algebra-foundations`).

---
