---
id: skill-4-eigenvalues-and-diagonalization-4c3694220f
purpose: 4 eigenvalues and diagonalization
source: src/vibey_tools/skills/plugins/calculus-geometry-algebra/skills/math-linear-algebra-foundations/SKILL.md
requires: ["skill-3-determinants-9ef9f4bda0"]
links: []
---

## §4. Eigenvalues and Diagonalization

`Av = λv` — ⚠️ **directions the map only stretches, without rotating.**
**Characteristic polynomial** `det(A − λI) = 0` — ⚠️ **fine for `2×2` by hand, and a
numerically catastrophic way to compute eigenvalues** (§8 → `math-inner-products-svd-and-numerical-reality`).

**Diagonalization** `A = PDP⁻¹` when there are `n` independent eigenvectors.
⚠️ **Then `Aᵏ = PDᵏP⁻¹`, which is why eigendecomposition makes iteration and matrix
exponentials tractable.**
> **⚠️ GOTCHA — not every matrix is diagonalizable.** ⚠️ **`[[1,1],[0,1]]` has one
> eigenvalue (1) with algebraic multiplicity 2 and geometric multiplicity 1.** **When
> geometric multiplicity is less than algebraic, the matrix is *defective* and you need
> the Jordan form.** ⚠️ **But Jordan form is numerically unstable — an arbitrarily small
> perturbation makes a defective matrix diagonalizable — so it's a theoretical tool, not
> a computational one. Use the Schur decomposition in practice** (§7 → `math-inner-products-svd-and-numerical-reality`).

**Trace = sum of eigenvalues; determinant = product.** ⚠️ **Both are basis-independent,
which is the §1 gotcha showing up again.**
**Cayley-Hamilton**: every matrix satisfies its own characteristic polynomial.
