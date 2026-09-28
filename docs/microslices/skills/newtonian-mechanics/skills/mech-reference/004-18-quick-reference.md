---
id: skill-18-quick-reference-843615e472
purpose: 18 quick reference
source: src/vibey_tools/skills/plugins/newtonian-mechanics/skills/mech-reference/SKILL.md
requires: ["skill-17-books-4b2c2f3558"]
links: ["skill-19-method-0aeee88144"]
---

## §18. Quick Reference

### 18.1 Problem-solving picker
| Situation | Approach |
|---|---|
| Forces known, want motion | **Free-body diagram + `ΣF = ma`** (§2.3 → `mech-kinematics-newtons-laws-and-forces`) |
| Don't care about time, know positions | ⚠️ **Energy conservation — far less algebra** (§4 → `mech-energy-momentum-and-collisions`) |
| Collision or explosion | ⚠️ **Momentum conservation; check if KE is conserved too** (§5 → `mech-energy-momentum-and-collisions`) |
| Short, violent interaction | **Impulse-momentum** (§5 → `mech-energy-momentum-and-collisions`) |
| Constraints everywhere (pendulums, linkages) | ⚠️ **Lagrangian — constraint forces vanish** (§11 → `mech-orbits-frames-analytical-mechanics-and-simulation`) |
| Want a conserved quantity | ⚠️ **Find the symmetry (Noether)** (§4.5 → `mech-energy-momentum-and-collisions`) |
| Rotating or accelerating frame | **Add fictitious forces** (§10 → `mech-orbits-frames-analytical-mechanics-and-simulation`) |
| Small oscillation about equilibrium | ⚠️ **Expand the potential — you'll get SHM** (§8 → `mech-rotation-rigid-bodies-and-oscillations`) |
| Central force | ⚠️ **Angular momentum conserved, motion is planar** (§9 → `mech-orbits-frames-analytical-mechanics-and-simulation`) |
| Simulating it | ⚠️ **Symplectic integrator, and monitor energy** (§14 → `mech-orbits-frames-analytical-mechanics-and-simulation`) |
| Long-duration orbital simulation | ⚠️ **Verlet, not RK4** (§14.2 → `mech-orbits-frames-analytical-mechanics-and-simulation`) |
| Stiff system | Implicit method (§14.3 → `mech-orbits-frames-analytical-mechanics-and-simulation`) |

### 18.2 Sanity checks
- [ ] **Dimensional analysis** — do the units work? ⚠️ **Catches most algebra errors free**
- [ ] **Limiting cases** — what happens as `m→0`, `θ→0`, `t→∞`? Does it match intuition?
- [ ] **Signs** — is the force in the direction physics says it should be?
- [ ] **Order of magnitude** — is the answer physically plausible?
- [ ] **Conserved quantities** — is energy/momentum conserved when it should be?
- [ ] **Free-body diagram**: can I name the object exerting every force I drew? (§2.3 → `mech-kinematics-newtons-laws-and-forces`)
- [ ] **Simulation**: is the conserved quantity drifting? (§14.3 → `mech-orbits-frames-analytical-mechanics-and-simulation`)

---
