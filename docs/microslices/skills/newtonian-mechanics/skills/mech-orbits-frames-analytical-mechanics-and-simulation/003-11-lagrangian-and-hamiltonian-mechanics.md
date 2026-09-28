---
id: skill-11-lagrangian-and-hamiltonian-mechanics-b2f24e954f
purpose: 11 lagrangian and hamiltonian mechanics
source: src/vibey_tools/skills/plugins/newtonian-mechanics/skills/mech-orbits-frames-analytical-mechanics-and-simulation/SKILL.md
requires: ["skill-10-non-inertial-frames-2f0c09b6d0"]
links: ["skill-12-fluids-and-continuous-media-briefly-000b91a9ec"]
---

## §11. Lagrangian and Hamiltonian Mechanics

**⚠️ Not new physics — a reformulation that is vastly more powerful for anything with
constraints.**

**Lagrangian** `L = T − V`, with the **Euler-Lagrange equations**:
```
d/dt (∂L/∂q̇ᵢ) − ∂L/∂qᵢ = 0
```
**⚠️ Why this is transformative:**
- **Constraint forces disappear.** ⚠️ **You never compute the normal force or the rod
  tension unless you want it** — choose generalized coordinates that already satisfy the
  constraints.
- **It's coordinate-independent.** Polar, spherical, whatever fits the problem.
- **It's scalar.** ⚠️ **No vector bookkeeping, no free-body diagrams.**
- **Symmetries become manifest**: ⚠️ **if `L` doesn't depend on a coordinate, its conjugate
  momentum is conserved — Noether's theorem falls out mechanically** (§4.5 → `mech-energy-momentum-and-collisions`).

**Hamiltonian** `H = Σp q̇ − L` — usually the total energy — with
```
q̇ = ∂H/∂p        ṗ = −∂H/∂q
```
**⚠️ First-order equations in phase space**, and the natural bridge to statistical
mechanics and quantum mechanics. **⚠️ Liouville's theorem — phase space volume is
conserved — is the property that §14's symplectic integrators are built to respect.**

**Principle of least action**: the actual path extremizes `S = ∫L dt`.
⚠️ **This is arguably the deepest formulation of classical mechanics**, and it generalizes
directly to field theory and quantum mechanics (Feynman's path integral).

---
