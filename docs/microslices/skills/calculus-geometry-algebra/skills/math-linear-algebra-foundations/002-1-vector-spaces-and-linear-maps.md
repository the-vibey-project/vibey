---
id: skill-1-vector-spaces-and-linear-maps-9c564fcf1a
purpose: 1 vector spaces and linear maps
source: src/vibey_tools/skills/plugins/calculus-geometry-algebra/skills/math-linear-algebra-foundations/SKILL.md
requires: ["skill-0-routing-9cc7389e7e"]
links: ["skill-2-matrices-and-the-four-fundamental-subspaces-7007c1e0b2"]
---

## §1. Vector Spaces and Linear Maps

**A vector space over a field**: closed under addition and scalar multiplication, with the
usual axioms. ⚠️ **"Vector" means "element of a vector space" — functions, polynomials,
matrices and random variables are all vectors, and treating them that way is the point of
the abstraction.**

**Span, linear independence, basis, dimension.** ⚠️ **Every vector space has a basis, and
all bases have the same cardinality — that's what makes dimension well defined.**

**Linear map**: `T(αu + βv) = αT(u) + βT(v)`.
> **⚠️ GOTCHA — a matrix is not a linear map; it's a *representation* of one in a chosen
> basis.** ⚠️ **Change the basis and the matrix changes while the map does not.**
> **Similar matrices `B = P⁻¹AP` represent the same map in different bases** — which is
> why they share eigenvalues, determinant, trace and rank. **Those are properties of the
> map; the entries are not.**

**Kernel** (null space) and **image** (range).
**⚠️ Rank-nullity**: `dim(ker T) + dim(im T) = dim(domain)`. **The single most used
theorem in the subject** — it's conservation of dimension.

---
