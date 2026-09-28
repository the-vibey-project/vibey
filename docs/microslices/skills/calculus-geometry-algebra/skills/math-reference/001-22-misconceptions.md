---
id: skill-22-misconceptions-9add343b62
purpose: 22 misconceptions
source: src/vibey_tools/skills/plugins/calculus-geometry-algebra/skills/math-reference/SKILL.md
requires: []
links: ["skill-23-formulas-b9f90779e1"]
---

## §22. Misconceptions

| Misconception | Correction |
|---|---|
| A matrix *is* a linear map | ⚠️ **It represents one in a chosen basis** (§1 → `math-linear-algebra-foundations`) |
| Eigendecomposition is the fundamental factorization | ⚠️ **SVD is — it always exists** (§6.1 → `math-inner-products-svd-and-numerical-reality`) |
| Every matrix is diagonalizable | ⚠️ **Defective matrices exist; use Schur, not Jordan** (§4 → `math-linear-algebra-foundations`, §7 → `math-inner-products-svd-and-numerical-reality`) |
| Determinant is a computational tool | ⚠️ **Conceptually central, computationally marginal** (§3 → `math-linear-algebra-foundations`) |
| Test `det = 0` for singularity | ⚠️ **Use σ_min or κ** (§3 → `math-linear-algebra-foundations`, §8 → `math-inner-products-svd-and-numerical-reality`) |
| Solve least squares via normal equations | ⚠️ **`AᵀA` squares the condition number. Use QR/SVD** (§5 → `math-inner-products-svd-and-numerical-reality`, §8 → `math-inner-products-svd-and-numerical-reality`) |
| Invert the matrix to solve `Ax = b` | ⚠️ **Solve the system — faster and more accurate** (§8 → `math-inner-products-svd-and-numerical-reality`) |
| Compute eigenvalues from the characteristic polynomial | ⚠️ **Polynomial roots are wildly ill-conditioned** (§8 → `math-inner-products-svd-and-numerical-reality`) |
| A better algorithm fixes an ill-conditioned problem | ⚠️ **Conditioning is the problem's property, not the algorithm's** (§8 → `math-inner-products-svd-and-numerical-reality`) |
| The derivative is the slope of the tangent | ⚠️ **It's the best linear approximation — that's what generalizes** (§9.2 → `math-calculus-and-vector-calculus`) |
| Smooth implies analytic | ⚠️ **`e^{−1/x²}` — false in real analysis, true in complex** (§11 → `math-calculus-and-vector-calculus`) |
| Green's, Stokes' and divergence are three theorems | ⚠️ **One theorem: `∫_∂M ω = ∫_M dω`** (§13 → `math-calculus-and-vector-calculus`, §14 → `math-forms-optimization-and-differential-equations`) |
| Curl-free implies conservative | ⚠️ **Only on a simply connected domain** (§13 → `math-calculus-and-vector-calculus`) |
| Fubini always lets you swap integration order | ⚠️ **Needs absolute integrability** (§12 → `math-calculus-and-vector-calculus`) |
| A conditionally convergent series has a sum | ⚠️ **Rearrangement gives any value you like** (§11 → `math-calculus-and-vector-calculus`) |
| Vectors and covectors are the same thing | ⚠️ **They coincide only in Euclidean space with an orthonormal basis** (§19 → `math-geometry-manifolds-tensors-and-lie-groups`) |
| A PyTorch tensor is a tensor | ⚠️ **It's an n-d array. A tensor is basis-independent** (§19 → `math-geometry-manifolds-tensors-and-lie-groups`) |
| Christoffel symbols are tensors | ⚠️ **They aren't — which is why they can vanish at a point** (§20 → `math-geometry-manifolds-tensors-and-lie-groups`) |
| You can compare vectors at different points on a manifold | ⚠️ **Not without a connection; the failure to do so IS curvature** (§18 → `math-geometry-manifolds-tensors-and-lie-groups`, §20 → `math-geometry-manifolds-tensors-and-lie-groups`) |
| Tensor decompositions inherit SVD's guarantees | ⚠️ **Order ≥3: best rank-k may not exist; rank is NP-hard** (§19 → `math-geometry-manifolds-tensors-and-lie-groups`) |
| High-dimensional critical points are usually minima | ⚠️ **Overwhelmingly saddles** (§12 → `math-calculus-and-vector-calculus`) |
| Optimize rotations by parameterizing the matrix | ⚠️ **Work in the Lie algebra** (§21 → `math-geometry-manifolds-tensors-and-lie-groups`) |

---
