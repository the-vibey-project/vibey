---
id: skill-3-determinants-9ef9f4bda0
purpose: 3 determinants
source: src/vibey_tools/skills/plugins/calculus-geometry-algebra/skills/math-linear-algebra-foundations/SKILL.md
requires: ["skill-2-matrices-and-the-four-fundamental-subspaces-7007c1e0b2"]
links: ["skill-4-eigenvalues-and-diagonalization-4c3694220f"]
---

## §3. Determinants

**⚠️ The definition to hold in your head: `det A` is the signed volume scaling factor of
the linear map.** A unit cube maps to a parallelepiped of volume `|det A|`; the sign
records orientation.
```
det A = 0        ⚠️ the map collapses dimension — not invertible
det(AB) = det(A)det(B)      ⚠️ scalings compose
det(Aᵀ) = det(A)      det(A⁻¹) = 1/det(A)
```
**⚠️ Practical warning**: **determinants are almost never the right computational tool.**
**Cramer's rule is `O(n!)` naively and numerically terrible; use LU. Testing `det = 0` for
singularity is unreliable — use the condition number or the smallest singular value**
(§8 → `math-inner-products-svd-and-numerical-reality`). **The determinant is conceptually central and computationally marginal.**

**⚠️ Where it genuinely matters**: the **Jacobian determinant** in change of variables
(§10 → `math-calculus-and-vector-calculus`, §12 → `math-calculus-and-vector-calculus`) — because that's exactly the local volume scaling.

---
