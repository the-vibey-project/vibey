---
id: skill-2-conditioning-and-stability-1e68a18599
purpose: 2 conditioning and stability
source: src/vibey_tools/skills/plugins/math-science-programming/skills/sci-floating-point-and-numerical-foundations/SKILL.md
requires: ["skill-1-floating-point-59b31b9f68"]
links: ["skill-3-the-substrate-blas-and-lapack-ab1bc3bcc7"]
---

## §2. Conditioning and Stability

**[DURABLE] The two concepts that let you reason about numerical error, and they're
distinct in a way people constantly conflate:**

- **Conditioning is a property of the *problem*.** How much does the output change when
  the input is perturbed? **An ill-conditioned problem amplifies error no matter how good
  your algorithm is.**
- **Stability is a property of the *algorithm*.** Does it introduce error beyond what the
  conditioning demands? **A backward-stable algorithm gives the exact answer to a slightly
  perturbed problem.**

**⚠️ The practical consequence: `error ≈ condition_number × machine_epsilon`.** For a
linear system with **κ(A) = 10^8** in float64, expect to lose about 8 of your ~16 digits.
**⚠️ κ(A) near 10^16 means you have no significant digits left, and the solver will not
warn you.** **Check the condition number.** `np.linalg.cond`, or `rcond` from the solver.

**Classic ill-conditioned traps**: **Hilbert matrices**, **Vandermonde matrices**
(⚠️ **which is why fitting a high-degree polynomial through `polyfit` on raw x-values is a
trap** — use orthogonal polynomials or scale the domain), **numerical differentiation**
(⚠️ **inherently ill-conditioned — halving h halves truncation error and doubles rounding
error; there's an optimal h around √ε and you cannot beat it**), **root-finding near
multiple roots**, and **deconvolution and inverse problems generally** (§8.4 → `sci-linear-algebra-differential-equations-and-optimization`).

**[DURABLE] The distinction that saves the most time**: **truncation error** comes from
your method (a finite difference, a truncated series) and shrinks as you refine;
**rounding error** comes from floating point and *grows* as you refine. ⚠️ **Total error
has a minimum. Refining past it makes your answer worse**, and watching an error curve
turn back upward is the standard diagnostic.

---
