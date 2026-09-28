---
id: skill-6-spectral-theorem-and-svd-8d6d3237d0
purpose: 6 spectral theorem and svd
source: src/vibey_tools/skills/plugins/calculus-geometry-algebra/skills/math-inner-products-svd-and-numerical-reality/SKILL.md
requires: ["skill-5-inner-products-and-orthogonality-c9d2893bd6"]
links: ["skill-7-matrix-factorizations-2f0e33a861"]
---

## §6. Spectral Theorem and SVD

**⚠️ Spectral theorem**: a **real symmetric** matrix has **real eigenvalues** and an
**orthonormal eigenbasis** — `A = QΛQᵀ`. **(Hermitian in the complex case.)**
⚠️ **This is why symmetric matrices are so much better behaved, and why covariance
matrices, Hessians, and Laplacians — all symmetric — are tractable.**
**Positive definite**: all eigenvalues > 0. ⚠️ **Equivalently `xᵀAx > 0` for all `x ≠ 0`,
equivalently it has a Cholesky factorization** (§7).

### 6.1 ⚠️ SVD — the most important factorization
```
A = UΣVᵀ        U (m×m) orthogonal, Σ (m×n) diagonal ≥0, V (n×n) orthogonal
```
> **⚠️ GOTCHA — SVD exists for EVERY matrix.** ⚠️ **Any shape, any rank, real or complex,
> no symmetry or invertibility required.** **Eigendecomposition needs square and often
> fails; SVD never does.** **If you learned eigendecomposition as the fundamental
> factorization, that's backwards — SVD is.**

**⚠️ What it says geometrically**: **every linear map is a rotation, then an axis-aligned
scaling, then another rotation.** That's all any linear map does.

**What it gives you:**
```
Rank             ⚠️ number of nonzero singular values — the RELIABLE rank test
Four subspaces   ⚠️ orthonormal bases for all of §2, directly
Condition number κ = σ_max/σ_min          (§8)
Pseudoinverse    A⁺ = VΣ⁺Uᵀ  ⚠️ solves least squares even for rank-deficient A
‖A‖₂ = σ_max     ‖A‖_F = √(Σσᵢ²)
Best rank-k approximation  ⚠️ Eckart-Young: truncate to the top k singular values.
                 OPTIMAL in both the 2-norm and Frobenius norm
```
**⚠️ Eckart-Young is the theorem behind an enormous amount of practice**: PCA (⚠️ **SVD of
centred data**), low-rank approximation, image compression, latent semantic analysis,
recommender systems, and model compression. **"Take the top k components" is always this
theorem.**

**⚠️ Relation to eigendecomposition**: singular values of `A` are square roots of
eigenvalues of `AᵀA`; **`V` holds its eigenvectors.** ⚠️ **But computing SVD that way
squares the condition number — real algorithms (Golub-Kahan) never form `AᵀA`.**

---
