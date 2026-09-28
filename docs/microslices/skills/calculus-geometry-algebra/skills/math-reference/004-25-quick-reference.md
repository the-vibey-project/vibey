---
id: skill-25-quick-reference-566e38b952
purpose: 25 quick reference
source: src/vibey_tools/skills/plugins/calculus-geometry-algebra/skills/math-reference/SKILL.md
requires: ["skill-24-books-a80dd8c174"]
links: ["skill-26-method-67af4155b8"]
---

## §25. Quick Reference

### 25.1 Picker
| Need | Use |
|---|---|
| Solve `Ax = b`, square, general | **LU with partial pivoting** (§7 → `math-inner-products-svd-and-numerical-reality`) |
| Solve `Ax = b`, symmetric positive definite | ⚠️ **Cholesky — twice as fast** (§7 → `math-inner-products-svd-and-numerical-reality`) |
| Least squares | ⚠️ **QR (or SVD if rank-deficient). Never normal equations** (§5 → `math-inner-products-svd-and-numerical-reality`, §7 → `math-inner-products-svd-and-numerical-reality`) |
| Rank, or numerical rank | ⚠️ **SVD — count singular values above tolerance** (§6.1 → `math-inner-products-svd-and-numerical-reality`) |
| Best low-rank approximation | ⚠️ **Truncated SVD (Eckart-Young)** (§6.1 → `math-inner-products-svd-and-numerical-reality`) |
| PCA | ⚠️ **SVD of centred data** (§6.1 → `math-inner-products-svd-and-numerical-reality`) |
| Is this problem well posed? | **Condition number** (§8 → `math-inner-products-svd-and-numerical-reality`) |
| Matrix powers or `e^{At}` | **Eigendecomposition, or Schur if defective** (§4 → `math-linear-algebra-foundations`, §16 → `math-forms-optimization-and-differential-equations`) |
| Huge sparse system | **Krylov (CG/GMRES) + ⚠️ a good preconditioner** (§7 → `math-inner-products-svd-and-numerical-reality`) |
| Direction of steepest ascent | **Gradient** (§12 → `math-calculus-and-vector-calculus`) |
| Classify a critical point | **Hessian eigenvalues** (§12 → `math-calculus-and-vector-calculus`) |
| Optimize with equality constraints | **Lagrange multipliers** (§15 → `math-forms-optimization-and-differential-equations`) |
| Optimize with inequality constraints | **KKT; ⚠️ check convexity for sufficiency** (§15 → `math-forms-optimization-and-differential-equations`) |
| Convert a boundary integral to a volume one | ⚠️ **Generalized Stokes** (§14 → `math-forms-optimization-and-differential-equations`) |
| High-dimensional integral | ⚠️ **Monte Carlo — error independent of dimension** (§10 → `math-calculus-and-vector-calculus`) |
| Represent rotations for optimization | ⚠️ **Lie algebra `so(3)`/`se(3)`** (§21 → `math-geometry-manifolds-tensors-and-lie-groups`) |
| Quantity that must be basis-independent | ⚠️ **Check it's actually a tensor** (§19 → `math-geometry-manifolds-tensors-and-lie-groups`) |

### 25.2 Sanity checks
- [ ] Dimensional/shape analysis — do the dimensions compose? (§1 → `math-linear-algebra-foundations`)
- [ ] Is my "tensor" basis-independent, or just an array? (§19 → `math-geometry-manifolds-tensors-and-lie-groups`)
- [ ] Am I forming `AᵀA` anywhere? ⚠️ **Don't** (§8 → `math-inner-products-svd-and-numerical-reality`)
- [ ] What's the condition number? (§8 → `math-inner-products-svd-and-numerical-reality`)
- [ ] Does this theorem's hypothesis actually hold — simply connected, absolutely integrable, convex, Lipschitz? (§11 → `math-calculus-and-vector-calculus`, §12 → `math-calculus-and-vector-calculus`, §13 → `math-calculus-and-vector-calculus`, §15 → `math-forms-optimization-and-differential-equations`, §16 → `math-forms-optimization-and-differential-equations`)
- [ ] Limiting cases: does the formula behave sensibly as parameters → 0 or ∞?
- [ ] Is the Taylor remainder small enough for the use I'm making of it? (§11 → `math-calculus-and-vector-calculus`)
- [ ] Am I comparing vectors at different points on a curved space? (§18 → `math-geometry-manifolds-tensors-and-lie-groups`)

---
