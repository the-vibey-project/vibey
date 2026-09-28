---
id: skill-23-formulas-b9f90779e1
purpose: 23 formulas
source: src/vibey_tools/skills/plugins/calculus-geometry-algebra/skills/math-reference/SKILL.md
requires: ["skill-22-misconceptions-9add343b62"]
links: ["skill-24-books-a80dd8c174"]
---

## §23. Formulas

```
LINEAR ALGEBRA
⚠️ Rank-nullity: dim ker + dim im = dim domain
Four subspaces: row ⊥ null (ℝⁿ), col ⊥ left-null (ℝᵐ)  ⚠️ dims r, n−r, r, m−r
det(AB) = det A det B · trace = Σλ · det = Πλ
Projection: P = A(AᵀA)⁻¹Aᵀ · Normal equations AᵀAx̂ = Aᵀb  ⚠️ (don't solve directly)
Spectral: A = QΛQᵀ (symmetric) · ⚠️ SVD: A = UΣVᵀ (ANY matrix)
κ(A) = σ_max/σ_min   ⚠️ lose ~k digits when κ ≈ 10ᵏ
⚠️ Eckart-Young: truncated SVD is the optimal rank-k approximation
Pseudoinverse A⁺ = VΣ⁺Uᵀ

CALCULUS
⚠️ f(a+h) = f(a) + f'(a)h + o(h)   — the definition that generalizes
FTC: d/dx ∫ₐˣf = f(x) · ∫ₐᵇf' = f(b) − f(a)
Taylor: f(x) = Σf⁽ⁿ⁾(a)(x−a)ⁿ/n!  ⚠️ + remainder
Chain rule (multivariable) = Jacobian product ⚠️ = backpropagation
∇×(∇f) = 0 · ∇·(∇×F) = 0   ⚠️ both are d² = 0
⚠️ GENERALIZED STOKES: ∫_∂M ω = ∫_M dω
Lagrange: ∇f = λ∇g · ⚠️ KKT adds μ ≥ 0 and μᵢgᵢ = 0

HESSIAN TEST
PD → min · ND → max · indefinite → ⚠️ saddle · singular → inconclusive

GEOMETRY & TENSORS
⚠️ Einstein summation: repeated upper-lower pairs sum
vⁱ contravariant (upper) · ωᵢ covariant (lower) · g_{ij} lowers, g^{ij} raises
Geodesic: ∇_γ̇ γ̇ = 0
⚠️ Theorema Egregium: Gaussian curvature is intrinsic
Riemann tensor ⚠️ = failure of parallel transport around a loop
Lie: exp: 𝔤 → G  ⚠️ optimize in the algebra, map back

NUMERICAL COSTS
LU O(n³/3) · Cholesky O(n³/6) · QR O(2mn²) · SVD O(mn²)
Trapezoid O(h²) · Simpson O(h⁴) · ⚠️ Monte Carlo O(N^{-1/2}), dimension-independent
```

---
