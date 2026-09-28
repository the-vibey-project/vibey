---
id: skill-7-matrix-factorizations-2f0e33a861
purpose: 7 matrix factorizations
source: src/vibey_tools/skills/plugins/calculus-geometry-algebra/skills/math-inner-products-svd-and-numerical-reality/SKILL.md
requires: ["skill-6-spectral-theorem-and-svd-8d6d3237d0"]
links: ["skill-8-conditioning-and-numerical-reality-7426d5ead6"]
---

## §7. Matrix Factorizations

| Factorization | Form | ⚠️ Use |
|---|---|---|
| **LU (with pivoting)** | `PA = LU` | ⚠️ **Solving `Ax=b`; the workhorse. `O(n³/3)`** |
| **Cholesky** | `A = LLᵀ` | ⚠️ **Symmetric positive definite; twice as fast as LU** |
| **QR** | `A = QR` | ⚠️ **Least squares, stably. Householder or Givens** |
| **Eigendecomposition** | `A = PDP⁻¹` | Dynamics, powers; ⚠️ may not exist |
| **Schur** | `A = QTQ*` | ⚠️ **Always exists, numerically stable — the practical alternative to Jordan** |
| **SVD** | `A = UΣVᵀ` | ⚠️ **Always exists; everything in §6.1** |
| **Jordan** | `A = PJP⁻¹` | ⚠️ **Theory only — numerically unstable** |

**Iterative methods for large sparse systems**: **Conjugate Gradient** (⚠️ **SPD only, and
Krylov-subspace based**), **GMRES**, **BiCGSTAB**; **Lanczos** and **Arnoldi** for
eigenvalues; ⚠️ **preconditioning is usually what determines whether these converge in
practice, and it matters more than the choice of solver.**
**Randomized SVD** — ⚠️ **for very large low-rank problems, and it works remarkably well.**

---
