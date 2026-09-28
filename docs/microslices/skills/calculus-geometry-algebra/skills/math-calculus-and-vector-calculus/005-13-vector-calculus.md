---
id: skill-13-vector-calculus-9e215a01b3
purpose: 13 vector calculus
source: src/vibey_tools/skills/plugins/calculus-geometry-algebra/skills/math-calculus-and-vector-calculus/SKILL.md
requires: ["skill-12-multivariable-calculus-87d6860d6f"]
links: []
---

## §13. Vector Calculus

```
grad   ∇f          scalar → vector      ⚠️ steepest ascent
div    ∇·F         vector → scalar      ⚠️ source/sink density
curl   ∇×F         vector → vector      ⚠️ circulation density (3D only)
lap    ∇²f = ∇·∇f  ⚠️ deviation from the local average — why it governs diffusion
```
**⚠️ Identities worth memorizing**: `∇×(∇f) = 0` (**gradients are curl-free**) and
`∇·(∇×F) = 0` (**curls are divergence-free**). ⚠️ **Both are `d² = 0` in disguise** (§14 → `math-forms-optimization-and-differential-equations`).

**The integral theorems:**
```
FTC (1D)               ∫ₐᵇ f' = f(b) − f(a)
Green's (2D)           ∮ (P dx + Q dy) = ∬ (∂Q/∂x − ∂P/∂y) dA
Stokes' (surface)      ∮ F·dr = ∬ (∇×F)·dS
Divergence/Gauss (3D)  ∯ F·dS = ∭ (∇·F) dV
```
> **⚠️ GOTCHA — these are four instances of ONE theorem, and teaching them separately is
> the biggest structural failure in the standard calculus sequence.** ⚠️ **All say: the
> integral of a derivative over a region equals the integral of the original over the
> boundary.** **§14 → `math-forms-optimization-and-differential-equations` makes this literal.**

**Conservative fields**: `F = ∇φ` ⟺ path-independent ⟺ `∮F·dr = 0` ⟺ `∇×F = 0`
⚠️ **(the last equivalence requires a simply connected domain — and the standard
counterexample on a punctured plane is where topology enters analysis).**
