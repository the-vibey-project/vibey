---
id: skill-3-the-substrate-blas-and-lapack-ab1bc3bcc7
purpose: 3 the substrate blas and lapack
source: src/vibey_tools/skills/plugins/math-science-programming/skills/sci-floating-point-and-numerical-foundations/SKILL.md
requires: ["skill-2-conditioning-and-stability-1e68a18599"]
links: []
---

## §3. The Substrate: BLAS and LAPACK

**[DURABLE] Almost everything numerical you will ever run bottoms out here, and knowing
that changes how you write code.**

**BLAS levels**: **Level 1** vector-vector, O(n) work on O(n) data — memory-bound.
**Level 2** matrix-vector, O(n²) on O(n²) — still memory-bound. **Level 3** matrix-matrix,
**O(n³) work on O(n²) data** — ⚠️ **compute-bound, cache-blockable, and the only level that
gets near peak FLOPS.** **This is why algorithms are reformulated in terms of matrix
products wherever possible.**

**LAPACK** builds the actual decompositions on top: LU, QR, Cholesky, SVD, eigenvalue
solvers. **Implementations**: **OpenBLAS**, **Intel MKL**, **AMD AOCL/BLIS**, **Apple
Accelerate**, and the **reference BLAS** (⚠️ **correct and slow — never use it for real
work**). **NumPy, MATLAB, R, and Julia are all calling these**, which is why
"MATLAB vs NumPy speed" comparisons on linear algebra usually measure which BLAS was
linked.

> **⚠️ GOTCHA — the vectorization principle.** In any interpreted array language,
> **the loop is the problem, not the language.** A Python loop over array elements runs at
> interpreter speed; the same operation expressed as an array operation runs at BLAS
> speed. **Two-to-three orders of magnitude, routinely.**
>
> ⚠️ **And the counter-caution: vectorizing can explode memory.** A broadcast that
> materializes an n×n intermediate for an O(n) result is a common and expensive mistake.
> Chunk it, or use an expression-fusing tool (`numexpr`, Numba, JAX).
