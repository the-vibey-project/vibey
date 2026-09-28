---
id: skill-19-tensors-done-properly-411640537b
purpose: 19 tensors done properly
source: src/vibey_tools/skills/plugins/calculus-geometry-algebra/skills/math-geometry-manifolds-tensors-and-lie-groups/SKILL.md
requires: ["skill-18-manifolds-f10e53c95b"]
links: ["skill-20-riemannian-geometry-1189c0a0d8"]
---

## §19. Tensors — Done Properly

**⚠️ Three definitions circulate, they are not equivalent, and the confusion is the single
most common problem in this area.**

```
1. ⚠️ "A multidimensional array"          — ML/programming usage
2. ⚠️ "An object transforming by a law"    — physics/engineering usage
3. ⚠️ "A multilinear map"                  — mathematics usage
```
> **⚠️ GOTCHA — a PyTorch tensor is generally NOT a tensor in the mathematical sense.**
> ⚠️ **It's an n-dimensional array — a data structure.** **A tensor in senses 2 and 3 is a
> basis-independent geometric object that *has* components in a basis, and those
> components must transform correctly under change of basis.**
> **The array is the shadow; the tensor is the object.** ⚠️ **This is exactly §1 → `math-linear-algebra-foundations`'s
> matrix-vs-linear-map distinction, one level up.** **Neither usage is wrong — but
> conflating them produces real errors when you start changing coordinates.**

**Definition 3 is the cleanest**: a **`(p,q)`-tensor** is a multilinear map taking `p`
covectors and `q` vectors to a scalar. `T: (V*)^p × V^q → ℝ`.

**Transformation law (definition 2)** — under a change of basis, ⚠️ **contravariant
(upper) indices transform with the Jacobian, covariant (lower) indices with its
inverse.** **That opposition is what makes contractions basis-independent.**
```
Vector (contravariant)      vⁱ       ⚠️ upper index
Covector/1-form (covariant) ωᵢ       ⚠️ lower index
Metric                      g_{ij}   ⚠️ (0,2) — lowers indices
Inverse metric              g^{ij}   raises them
```
**⚠️ Einstein summation**: repeated upper-lower index pairs are summed. **`vⁱωᵢ` is a
scalar.**
**Operations**: **outer product** (raises rank), **contraction** (⚠️ **lowers rank by 2;
trace is a contraction**), **raising and lowering with the metric** (⚠️ **which is why the
vector/covector distinction is invisible in Euclidean space with an orthonormal basis —
`g = I`, so components coincide, and that's precisely why the distinction is never taught
in introductory courses and then causes trouble later**).

**Examples**: **stress tensor** (rank 2), **metric tensor** (rank 2), **Riemann curvature**
(rank 4), **moment of inertia** (rank 2 — ⚠️ **and the reason `L` and `ω` need not be
parallel; see a Newtonian-mechanics reference §7**), **electromagnetic field tensor**.

**⚠️ Tensor decompositions** (a genuinely different topic that shares the name): **CP/PARAFAC**,
**Tucker**, **tensor trains**. ⚠️ **Here "tensor" means definition 1, and the SVD analogy is
imperfect — for order ≥ 3, best rank-k approximation may not exist, and computing tensor
rank is NP-hard.** **Do not assume §6.1 → `math-inner-products-svd-and-numerical-reality`'s guarantees carry over.**

---
