---
id: skill-20-riemannian-geometry-1189c0a0d8
purpose: 20 riemannian geometry
source: src/vibey_tools/skills/plugins/calculus-geometry-algebra/skills/math-geometry-manifolds-tensors-and-lie-groups/SKILL.md
requires: ["skill-19-tensors-done-properly-411640537b"]
links: ["skill-21-lie-groups-and-algebras-c151760c46"]
---

## §20. Riemannian Geometry

**Metric tensor `g`** — ⚠️ **an inner product on each tangent space, varying smoothly.**
**It gives lengths, angles, volumes, and geodesics.**
**Connection / covariant derivative `∇`** — ⚠️ **how to differentiate vector fields, i.e.
how to compare tangent spaces (§18).** **The Levi-Civita connection is the unique
torsion-free, metric-compatible one, with Christoffel symbols `Γᵏᵢⱼ` built from
derivatives of `g`.**
⚠️ **Christoffel symbols are NOT tensors** — they don't transform correctly, which is
exactly why they can be made to vanish at a point (normal coordinates).

**Geodesics** — ⚠️ **straightest possible paths, `∇_γ̇ γ̇ = 0`; locally length-minimizing.**
**Curvature**: **Riemann tensor `R^ρ_{σμν}`** (⚠️ **measures failure of parallel transport
around an infinitesimal loop to return the original vector — the §18 gotcha made
quantitative**), **Ricci `R_{μν}`** (a contraction), **scalar `R`**, **sectional**, and
**Gaussian** curvature.
**⚠️ Gauss's Theorema Egregium**: **Gaussian curvature is intrinsic** — ⚠️ **measurable
from inside the surface without reference to any embedding.** **This is why a flat map of
the sphere must distort, and why the result is called "remarkable."**
**⚠️ Gauss-Bonnet** links total curvature to the Euler characteristic — **geometry
constrained by topology.**

---
