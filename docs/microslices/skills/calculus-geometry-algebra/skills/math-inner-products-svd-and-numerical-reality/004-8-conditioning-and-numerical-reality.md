---
id: skill-8-conditioning-and-numerical-reality-7426d5ead6
purpose: 8 conditioning and numerical reality
source: src/vibey_tools/skills/plugins/calculus-geometry-algebra/skills/math-inner-products-svd-and-numerical-reality/SKILL.md
requires: ["skill-7-matrix-factorizations-2f0e33a861"]
links: []
---

## §8. Conditioning and Numerical Reality

**Condition number** `κ(A) = σ_max/σ_min` — ⚠️ **how much relative input error is
amplified.**
```
κ ≈ 1        well conditioned
κ ≈ 10ᵏ      ⚠️ expect to lose about k digits of accuracy
κ = ∞        singular
```
**⚠️ Double precision gives ~16 digits, so `κ > 10¹⁶` means no correct digits remain.**

> **⚠️ GOTCHA — conditioning is a property of the PROBLEM; stability is a property of the
> ALGORITHM.** ⚠️ **A backward-stable algorithm on an ill-conditioned problem still gives
> a bad answer, and that is not the algorithm's fault.** **You cannot fix ill-conditioning
> with better code — you must reformulate the problem.**

**⚠️ The specific things not to do**, all of which follow from the above:
- **Don't form `AᵀA`** (§5) — ⚠️ **it squares `κ`.** Use QR or SVD.
- **Don't compute eigenvalues from the characteristic polynomial** — ⚠️ **polynomial roots
  are wildly ill-conditioned (Wilkinson's polynomial).**
- **Don't invert a matrix to solve `Ax = b`** — ⚠️ **solve the system. Inversion is slower
  and less accurate.**
- **Don't test `det = 0`** for singularity (§3 → `math-linear-algebra-foundations`) — use `σ_min` or `κ`.
- **Don't use classical Gram-Schmidt** (§5).
- ⚠️ **Don't subtract nearly equal numbers** — catastrophic cancellation destroys
  significant digits. **This is why the quadratic formula needs a rearranged branch.**

---

# PART II — CALCULUS
