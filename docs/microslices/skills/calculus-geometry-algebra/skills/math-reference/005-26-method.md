---
id: skill-26-method-67af4155b8
purpose: 26 method
source: src/vibey_tools/skills/plugins/calculus-geometry-algebra/skills/math-reference/SKILL.md
requires: ["skill-25-quick-reference-566e38b952"]
links: []
---

## §26. Method

**No searches were run; none could be relevant.** ⚠️ **This is the most settled material
in the series.** **Newton and Leibniz (1670s)**, **Gauss**, **Cauchy's rigorous limits
(1820s)**, **Grassmann (1844)**, **Riemann (1854)**, **Ricci-Curbastro and Levi-Civita
(1890s)**, **Cartan's exterior calculus (1899)**, **Eckart-Young (1936)**. ⚠️ **None of
it will change.**

**Sources** are the texts in §24 — chiefly **Strang** and **Axler** for §1–§6 → `math-linear-algebra-foundations`, `math-inner-products-svd-and-numerical-reality`,
**Trefethen & Bau** for §7–§8 → `math-inner-products-svd-and-numerical-reality`, **Spivak** and **Hubbard & Hubbard** for §9–§15 → `math-calculus-and-vector-calculus`, `math-forms-optimization-and-differential-equations`, **Lee**
and **do Carmo** for §17–§21 → `math-geometry-manifolds-tensors-and-lie-groups`, and **Boyd & Vandenberghe** for §15 → `math-forms-optimization-and-differential-equations`.

**Confidence: high throughout**, ⚠️ **and I have stated theorems with their hypotheses,
because in mathematics the hypotheses are the theorem.** **§22 is largely a list of
results applied outside their conditions.**

⚠️ **Four editorial choices worth naming, since they shape what's emphasized.**

**§6.1 → `math-inner-products-svd-and-numerical-reality` gives SVD priority over eigendecomposition, deliberately.** ⚠️ **Standard curricula
teach eigendecomposition first and often never reach SVD properly, which leaves people
with the fundamental factorization backwards.** **SVD exists for every matrix, gives all
four subspaces, the condition number, the pseudoinverse, and the optimal low-rank
approximation.** **Eigendecomposition needs a square matrix and can fail.** ⚠️ **If you
retain one thing from Part I, retain SVD.**

**§13 → `math-calculus-and-vector-calculus` and §14 → `math-forms-optimization-and-differential-equations` present the integral theorems as one theorem.** ⚠️ **Teaching Green's,
Stokes' and the divergence theorem as three separate formulas is, I'd argue, the largest
structural failure in the standard calculus sequence** — **students memorize three things
that are one thing, and the unifying statement `∫_∂M ω = ∫_M dω` is both simpler and more
powerful.** **Hubbard & Hubbard and Spivak's *Calculus on Manifolds* both take this route
and it's worth the detour.**

**§19 → `math-geometry-manifolds-tensors-and-lie-groups` is the section I'd most want read by anyone working in machine learning.** ⚠️ **The
word "tensor" carries three inequivalent meanings, and the ML usage is the one that is
*not* the mathematical object.** **A PyTorch tensor is a data structure; a tensor proper
is basis-independent and defined by how its components transform.** ⚠️ **The distinction is
harmless until you change coordinates, and then it isn't.** **It is precisely §1 → `math-linear-algebra-foundations`'s
matrix-versus-linear-map problem one level up, which is why I've placed them as bookends.**

**§8 → `math-inner-products-svd-and-numerical-reality`'s numerical warnings are included because they're the gap between knowing the
mathematics and getting a correct answer.** ⚠️ **Every item in that section is something
that is mathematically valid and numerically wrong** — the normal equations, the
characteristic polynomial, matrix inversion, `det = 0`. **Trefethen & Bau is the book that
fixes this, and it's genuinely a pleasure to read, which is rare in numerical analysis.**
