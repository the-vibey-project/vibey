---
id: skill-9-the-derivative-27dad5bf72
purpose: 9 the derivative
source: src/vibey_tools/skills/plugins/calculus-geometry-algebra/skills/math-calculus-and-vector-calculus/SKILL.md
requires: []
links: ["skill-10-integration-78fd6c9f2f"]
---

## §9. The Derivative

### 9.1 Limits and continuity
**`lim_{x→a} f(x) = L`** — ⚠️ **the ε-δ definition is what makes the subject rigorous, and
it exists to handle exactly the cases intuition fails on.**
**Continuity** at `a`: the limit exists and equals `f(a)`.
**⚠️ Uniform continuity** is stronger — one δ works everywhere; **and it's what you need for
theorems about integrability.**
**Key theorems on compact intervals**: **Intermediate Value**, **Extreme Value**, **Mean
Value** (⚠️ **the workhorse — most of single-variable calculus's theory is corollaries of
MVT**).

### 9.2 ⚠️ What the derivative actually is
```
f(a + h) = f(a) + f'(a)h + o(h)
```
> **⚠️ GOTCHA — the derivative is the best LINEAR APPROXIMATION at a point, and this is
> the definition worth carrying.** ⚠️ **"Slope of the tangent line" is a 1D picture;
> "limit of difference quotients" is a computation.** **Neither generalizes.**
> **The linear-approximation view generalizes immediately**: ⚠️ **in `ℝⁿ → ℝᵐ` the
> derivative is a linear map (the Jacobian); on a manifold it's a map between tangent
> spaces (§18 → `math-geometry-manifolds-tensors-and-lie-groups`); in a function space it's the Fréchet derivative.** **Same idea
> throughout.**

**Rules**: product, quotient, **chain rule** (⚠️ **which is just composition of linear
approximations — that's why it's a product**).
**⚠️ Differentiable ⟹ continuous, but not conversely** (`|x|` at 0; **and Weierstrass's
function is continuous everywhere and differentiable nowhere**).

---
