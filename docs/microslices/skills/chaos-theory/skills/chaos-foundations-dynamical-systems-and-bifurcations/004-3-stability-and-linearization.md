---
id: skill-3-stability-and-linearization-6e637cca70
purpose: 3 stability and linearization
source: src/vibey_tools/skills/plugins/chaos-theory/skills/chaos-foundations-dynamical-systems-and-bifurcations/SKILL.md
requires: ["skill-2-dynamical-systems-bc9348511c"]
links: ["skill-4-bifurcations-a0af6760ea"]
---

## §3. Stability and Linearization

**Fixed points**: `f(x*) = 0` (flows) or `f(x*) = x*` (maps).
**Linearize**: compute the **Jacobian** at the fixed point and examine its eigenvalues.
```
FLOWS                          MAPS
Re(λ) < 0 all      stable      |λ| < 1 all      stable
Re(λ) > 0 any      unstable    |λ| > 1 any      unstable
Re(λ) = 0          ⚠️ MARGINAL — linearization tells you nothing
```
**Classification in 2D**: node, saddle (⚠️ **stable in one direction, unstable in another —
and saddles organize global dynamics via their stable and unstable manifolds**), focus/
spiral, centre.

**⚠️ The Hartman-Grobman theorem** says the nonlinear flow is topologically conjugate to
its linearization **near a hyperbolic fixed point** — ⚠️ **hyperbolic meaning no eigenvalue
on the imaginary axis.** **This is what licenses linearization, and it fails exactly at
the marginal cases — which is precisely where bifurcations happen** (§4). **The
interesting cases are the ones where linear analysis is invalid.**

**⚠️ Stable and unstable manifolds** of a saddle are the global objects that matter. **When
a stable and an unstable manifold intersect transversally, you get a homoclinic tangle —
and that is chaos** (§10 → `chaos-fractals-poincare-and-hamiltonian-chaos`).

---
