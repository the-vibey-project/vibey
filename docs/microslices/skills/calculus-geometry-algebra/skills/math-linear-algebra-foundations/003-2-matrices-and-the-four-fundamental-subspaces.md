---
id: skill-2-matrices-and-the-four-fundamental-subspaces-7007c1e0b2
purpose: 2 matrices and the four fundamental subspaces
source: src/vibey_tools/skills/plugins/calculus-geometry-algebra/skills/math-linear-algebra-foundations/SKILL.md
requires: ["skill-1-vector-spaces-and-linear-maps-9c564fcf1a"]
links: ["skill-3-determinants-9ef9f4bda0"]
---

## §2. Matrices and the Four Fundamental Subspaces

**⚠️ Strang's framing, and it organizes everything:** for `A: ℝⁿ → ℝᵐ`,
```
Column space  C(A)   ⊆ ℝᵐ   dim = r          ⚠️ where Ax can land
Null space    N(A)   ⊆ ℝⁿ   dim = n − r      ⚠️ what A destroys
Row space     C(Aᵀ)  ⊆ ℝⁿ   dim = r
Left null     N(Aᵀ)  ⊆ ℝᵐ   dim = m − r
```
**⚠️ The orthogonality relations are the content**: **row space ⊥ null space in ℝⁿ**, and
**column space ⊥ left null space in ℝᵐ.** ⚠️ **Each pair decomposes its whole space.**
**`Ax = b` is solvable exactly when `b ∈ C(A)`, and the solution set is a particular
solution plus `N(A)`.**

**Rank** — ⚠️ **row rank equals column rank, which is not obvious and is the reason the
picture above is symmetric.**
**Matrix multiplication is composition of maps** — ⚠️ **which is why it's associative and
not commutative, and both facts stop being surprising once you see it.**

---
