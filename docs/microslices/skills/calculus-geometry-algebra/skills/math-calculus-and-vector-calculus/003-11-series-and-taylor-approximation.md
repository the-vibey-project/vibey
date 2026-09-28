---
id: skill-11-series-and-taylor-approximation-64c180bbe8
purpose: 11 series and taylor approximation
source: src/vibey_tools/skills/plugins/calculus-geometry-algebra/skills/math-calculus-and-vector-calculus/SKILL.md
requires: ["skill-10-integration-78fd6c9f2f"]
links: ["skill-12-multivariable-calculus-87d6860d6f"]
---

## §11. Series and Taylor Approximation

**Convergence tests**: ratio, root, comparison, integral, alternating.
⚠️ **Absolute vs conditional convergence matters**: **a conditionally convergent series can
be rearranged to converge to any value whatsoever (Riemann rearrangement).**

**Taylor series**:
```
f(x) = Σ f⁽ⁿ⁾(a)(x−a)ⁿ/n!
```
**⚠️ With the remainder term — the remainder is the part that matters and the part that
gets dropped.** **Lagrange form: `R_n = f⁽ⁿ⁺¹⁾(ξ)(x−a)ⁿ⁺¹/(n+1)!`.**
> **⚠️ GOTCHA — a function can be infinitely differentiable and NOT equal its Taylor
> series.** ⚠️ **`e^{−1/x²}` (with `f(0)=0`) has every derivative zero at the origin, so
> its Taylor series is identically zero, while the function is not.** **Smooth does not
> imply analytic.** ⚠️ **In complex analysis this cannot happen — differentiable once
> implies analytic — which is a genuinely deep difference between real and complex
> analysis.**

**Radius of convergence**, **Fourier series** (⚠️ **expansion in an orthogonal basis of
functions — which is §5 → `math-inner-products-svd-and-numerical-reality` in an infinite-dimensional space, and seeing it that way makes it
much less mysterious**), and **asymptotic series** (⚠️ **divergent yet useful — truncating
at the right term gives excellent accuracy, and adding more terms makes it worse**).

---
