---
id: skill-5-symbolic-computation-53191c1342
purpose: 5 symbolic computation
source: src/vibey_tools/skills/plugins/math-science-programming/skills/sci-tooling-and-symbolic-computation/SKILL.md
requires: ["skill-4-choosing-a-tool-40792f3502"]
links: []
---

## §5. Symbolic Computation

**[DURABLE] A genuinely different mode: exact manipulation of expressions, not
approximation of numbers.**

**Tools**: **Mathematica** (⚠️ **the most capable, and it's not close for hard integration
and simplification**), **Maple**, **SymPy** (Python, free, ⚠️ **capable but notably slower
and weaker at hard simplification**), **SymEngine** (fast C++ core), **Maxima**, **SageMath**
(an integrating layer over many systems), and **Symbolics.jl**.

**What it's genuinely good for**: **deriving equations of motion, Jacobians, and gradients**
(⚠️ **and then generating code from them — the single most valuable pattern here**),
symbolic integration and differentiation, exact linear algebra over small matrices, series
expansions, and **checking your hand derivation.**

> **⚠️ GOTCHA — the failure modes.** **Expression swell**: intermediate expressions grow
> exponentially and a "simple" symbolic solve consumes all memory. **Simplification is
> undecidable in general**, so `simplify()` is heuristic and may not find the form you
> want. **Most equations have no closed-form solution** — symbolic tools will tell you so,
> eventually, after a long time. **And branch cuts and assumptions** (is `x` real?
> positive?) silently change answers. **⚠️ Declare your assumptions explicitly.**

**[DURABLE] The three-way distinction worth holding**: **symbolic** (exact, slow, may not
terminate), **automatic differentiation** (⚠️ **exact derivatives of a *program*, at
numerical speed — this is what changed scientific computing, and it is neither symbolic
nor finite-difference**), and **numerical differentiation** (approximate,
ill-conditioned — §2 → `sci-floating-point-and-numerical-foundations`). **For gradients of code, AD is almost always the right answer**:
JAX, PyTorch, Enzyme, ForwardDiff.jl, or Zygote.jl.
