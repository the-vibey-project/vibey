---
id: skill-16-differential-equations-b484159deb
purpose: 16 differential equations
source: src/vibey_tools/skills/plugins/calculus-geometry-algebra/skills/math-forms-optimization-and-differential-equations/SKILL.md
requires: ["skill-15-constrained-optimization-b8623736d5"]
links: []
---

## §16. Differential Equations

**ODEs**: separable, linear (integrating factor), exact, **constant-coefficient linear**
(⚠️ **solved by the characteristic equation, which is §4 → `math-linear-algebra-foundations`'s eigenvalue problem**).
**Systems `ẋ = Ax`** have solution `x(t) = e^{At}x₀` — ⚠️ **and the matrix exponential is
computed via eigendecomposition, so stability is read off the eigenvalues: `Re(λ) < 0` for
all λ means stable.** **Existence and uniqueness (Picard-Lindelöf) requires Lipschitz
continuity.**

**PDEs** by type, and ⚠️ **the classification determines everything about behaviour and
numerics:**
```
Elliptic    (Laplace, Poisson)   ⚠️ equilibrium; boundary-value; smooth solutions
Parabolic   (heat)               ⚠️ diffusion; smooths data; irreversible
Hyperbolic  (wave)               ⚠️ finite propagation speed; preserves discontinuities
```
**Methods**: separation of variables, **Fourier and Laplace transforms** (⚠️ **which turn
differentiation into multiplication — the reason transform methods work at all**), Green's
functions, characteristics.

---

# PART III — GEOMETRY AND TENSORS
