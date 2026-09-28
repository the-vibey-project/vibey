---
id: skill-5-inner-products-and-orthogonality-c9d2893bd6
purpose: 5 inner products and orthogonality
source: src/vibey_tools/skills/plugins/calculus-geometry-algebra/skills/math-inner-products-svd-and-numerical-reality/SKILL.md
requires: []
links: ["skill-6-spectral-theorem-and-svd-8d6d3237d0"]
---

## §5. Inner Products and Orthogonality

**Inner product** `⟨u,v⟩` — gives length `‖v‖ = √⟨v,v⟩` and angle `cos θ = ⟨u,v⟩/(‖u‖‖v‖)`.
⚠️ **Geometry enters linear algebra here and not before. A vector space has no notion of
length or angle until you choose an inner product.**

**Orthonormal bases** are the good ones: ⚠️ **coefficients are just inner products,
`v = Σ⟨v,eᵢ⟩eᵢ`, with no linear system to solve.**
**Gram-Schmidt** constructs them — ⚠️ **and classical Gram-Schmidt is numerically unstable;
use modified Gram-Schmidt or Householder** (§7).

**Projection onto a subspace**: `P = A(AᵀA)⁻¹Aᵀ`.
**⚠️ Least squares is projection.** `Ax = b` with no solution → project `b` onto `C(A)`:
```
Normal equations: AᵀAx̂ = Aᵀb
```
⚠️ **But do not solve the normal equations numerically — forming `AᵀA` squares the
condition number** (§8). **Use QR or SVD.**
**⚠️ The residual is orthogonal to the column space, and that's the entire geometric
content of least squares.**

**Orthogonal matrices** `QᵀQ = I` — ⚠️ **preserve lengths and angles, `det = ±1`, and are
perfectly conditioned. This is why numerical algorithms are built from them.**

---
