---
id: skill-10-integration-78fd6c9f2f
purpose: 10 integration
source: src/vibey_tools/skills/plugins/calculus-geometry-algebra/skills/math-calculus-and-vector-calculus/SKILL.md
requires: ["skill-9-the-derivative-27dad5bf72"]
links: ["skill-11-series-and-taylor-approximation-64c180bbe8"]
---

## §10. Integration

**Riemann integral** — limit of tapering partitions. **Fundamental Theorem of Calculus**:
```
d/dx ∫ₐˣ f(t)dt = f(x)        ∫ₐᵇ f'(x)dx = f(b) − f(a)
```
⚠️ **Differentiation and integration are inverse operations — the central insight of the
whole subject, and it was not obvious to anyone before Newton and Leibniz.**

**⚠️ Lebesgue integration** — partition the *range* rather than the domain. **Why it
matters**: it integrates far more functions, and ⚠️ **crucially, it has good convergence
theorems (monotone and dominated convergence) that let you exchange limits and integrals.**
**Riemann's don't.** **This is why probability theory and functional analysis are built on
Lebesgue.**

**Techniques**: substitution (⚠️ **the chain rule backwards**), integration by parts
(⚠️ **the product rule backwards, and the source of the adjoint relationships throughout
physics**), partial fractions, trigonometric substitution, contour integration.
**Improper integrals** and convergence tests.

**⚠️ Numerical integration**: trapezoid `O(h²)`, Simpson `O(h⁴)`, **Gaussian quadrature**
(⚠️ **exact for polynomials up to degree `2n−1` with `n` points — remarkably efficient**),
**adaptive methods**, and ⚠️ **Monte Carlo, whose `O(N^{-1/2})` error is dimension-
independent — which is why it wins in high dimensions despite being slow in low ones.**

---
