---
id: skill-9-fractals-and-dimension-bbfc8d6ec4
purpose: 9 fractals and dimension
source: src/vibey_tools/skills/plugins/chaos-theory/skills/chaos-fractals-poincare-and-hamiltonian-chaos/SKILL.md
requires: []
links: ["skill-10-poincar-sections-and-symbolic-dynamics-0e3fe813d5"]
---

## §9. Fractals and Dimension

**⚠️ Self-similarity across scales**, and **non-integer dimension.**
```
Box-counting: D₀ = lim (log N(ε) / log(1/ε))
Cantor set     D = ln2/ln3 ≈ 0.631
Koch curve     D = ln4/ln3 ≈ 1.262
Sierpinski     D = ln3/ln2 ≈ 1.585
⚠️ Lorenz attractor ≈ 2.06
```
**Dimension types**: **box-counting `D₀`** (geometry only), **information `D₁`**,
**correlation `D₂`** (⚠️ **the one estimable from data, via Grassberger-Procaccia — §12 → `chaos-detection-control-applications-and-computation`**),
and the **Kaplan-Yorke dimension** computed from the Lyapunov spectrum ⚠️ **which links the
dynamics to the geometry directly.**

**⚠️ The Mandelbrot set is not a chaotic attractor and is frequently miscategorized.** It's
the set of `c` for which the orbit of 0 under `z → z² + c` stays bounded — **a picture of
parameter space, not of a trajectory.** ⚠️ **Its boundary encodes bifurcation structure**
(the period-doubling cascade of §5 → `chaos-logistic-map-lyapunov-and-attractors` is visible along the real axis), **but it is a
different kind of object from a strange attractor.**

**⚠️ Fractal geometry and chaotic dynamics are related but distinct.** **Coastlines and
snowflakes are fractal and not chaotic; strange attractors are both.** **Conflating them
is a standard error** (§16 → `chaos-reference`).

---
