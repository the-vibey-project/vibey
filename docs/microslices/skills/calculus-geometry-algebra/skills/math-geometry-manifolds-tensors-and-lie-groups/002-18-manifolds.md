---
id: skill-18-manifolds-f10e53c95b
purpose: 18 manifolds
source: src/vibey_tools/skills/plugins/calculus-geometry-algebra/skills/math-geometry-manifolds-tensors-and-lie-groups/SKILL.md
requires: ["skill-17-geometry-5088736bb3"]
links: ["skill-19-tensors-done-properly-411640537b"]
---

## §18. Manifolds

**⚠️ A space that looks locally like `ℝⁿ`** — charts, atlases, transition maps.
**Smooth manifold**: transition maps are smooth.
**Tangent space `T_pM`** — ⚠️ **the vector space of directions at a point.** **Formally
defined via derivations or equivalence classes of curves, precisely because you cannot
subtract points on a curved space.**
> **⚠️ GOTCHA — you cannot compare vectors at different points on a manifold.** ⚠️ **There
> is no canonical way to say a vector here "equals" a vector there.** **Fixing this
> requires a connection**, and **the failure of parallel transport around a closed loop
> to return the original vector is exactly curvature** (§20). **This is the conceptual
> core of differential geometry.**

**Vector fields**, **cotangent space** `T*_pM` (⚠️ **the dual — where 1-forms live, and
where gradients actually live**), **tensor and exterior bundles**, **flows and Lie
brackets**.

---
