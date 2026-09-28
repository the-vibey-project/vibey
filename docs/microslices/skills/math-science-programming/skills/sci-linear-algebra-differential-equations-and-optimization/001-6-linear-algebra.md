---
id: skill-6-linear-algebra-a33ab9478a
purpose: 6 linear algebra
source: src/vibey_tools/skills/plugins/math-science-programming/skills/sci-linear-algebra-differential-equations-and-optimization/SKILL.md
requires: []
links: ["skill-7-differential-equations-and-simulation-8466f9074a"]
---

## §6. Linear Algebra

**[DURABLE] The most important practical rule in this entire document:**

> **⚠️ GOTCHA — never invert a matrix to solve a linear system.**
> `x = inv(A) @ b` is slower, less accurate, and less numerically stable than
> `x = solve(A, b)`. **The explicit inverse is almost never what you want** — if you find
> yourself computing one, you are probably solving a system, and there is a factorization
> for it. **Same for `det(A)` as a singularity test: it overflows, underflows, and tells
> you less than the condition number does.**

**Pick the factorization to match the matrix**:

| Structure | Use | Cost |
|---|---|---|
| **General square** | **LU with partial pivoting** | ~⅔n³ |
| **Symmetric positive definite** | ⚠️ **Cholesky — 2× faster and more stable. Use it whenever it applies** | ~⅓n³ |
| **Least squares / overdetermined** | ⚠️ **QR, not the normal equations** — forming AᵀA **squares the condition number** | ~2mn² |
| **Rank-deficient, ill-conditioned, or you need structure** | **SVD** — ⚠️ **the most informative and most expensive** | ~O(mn²) |
| **Symmetric eigenproblem** | Symmetric QR / divide-and-conquer | |
| **Large sparse** | **Iterative: CG (SPD), GMRES/BiCGSTAB (general), LSQR** | Depends |

**⚠️ Sparse is a different discipline.** Store in CSR/CSC/COO; ⚠️ **fill-in during
factorization is the central problem**, mitigated by reordering (AMD, METIS). **Iterative
methods live or die by preconditioning** — ⚠️ **an unpreconditioned Krylov solver on a
poorly-conditioned system will converge slowly or not at all, and "not converging" is the
default state.** Jacobi, ILU, algebraic multigrid, domain decomposition.

**Libraries**: **SuiteSparse** (⚠️ **Tim Davis's work — UMFPACK, CHOLMOD; the standard**),
**PETSc** and **Trilinos** for large-scale parallel, **Eigen** (C++ header-only),
**ARPACK** for large eigenproblems, **cuSOLVER/cuSPARSE** on GPU.

---
