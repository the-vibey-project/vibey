---
id: skill-19-quick-reference-27582997f6
purpose: 19 quick reference
source: src/vibey_tools/skills/plugins/chaos-theory/skills/chaos-reference/SKILL.md
requires: ["skill-18-books-e981b5566f"]
links: ["skill-20-method-907b7ec620"]
---

## §19. Quick Reference

### 19.1 Picker
| Question | Approach |
|---|---|
| Is this fixed point stable? | **Jacobian eigenvalues** (§3 → `chaos-foundations-dynamical-systems-and-bifurcations`) |
| What happens as I vary a parameter? | **Bifurcation diagram; continuation software** (§4 → `chaos-foundations-dynamical-systems-and-bifurcations`) |
| Is this system chaotic? | ⚠️ **Largest Lyapunov exponent > 0** (§6 → `chaos-logistic-map-lyapunov-and-attractors`) |
| How far ahead can I predict? | ⚠️ **`(1/λ)ln(tolerance/δ₀)`** (§6 → `chaos-logistic-map-lyapunov-and-attractors`) |
| Chaos in a continuous system? | ⚠️ **Need ≥3 dimensions** (§2 → `chaos-foundations-dynamical-systems-and-bifurcations`) |
| Visualize a 3D attractor's structure | **Poincaré section** (§10 → `chaos-fractals-poincare-and-hamiltonian-chaos`) |
| Reconstruct dynamics from one measured signal | ⚠️ **Takens delay embedding** (§12 → `chaos-detection-control-applications-and-computation`) |
| Is this data chaotic or just noisy? | ⚠️ **Surrogate data testing — and expect "noisy"** (§12 → `chaos-detection-control-applications-and-computation`) |
| Prove chaos rigorously | **Find an embedded horseshoe** (§10 → `chaos-fractals-poincare-and-hamiltonian-chaos`) |
| Stabilize a chaotic system | ⚠️ **OGY or delayed feedback — small perturbations suffice** (§13 → `chaos-detection-control-applications-and-computation`) |
| Simulate a Hamiltonian chaotic system | ⚠️ **Symplectic integrator** (§15 → `chaos-detection-control-applications-and-computation`) |
| Long-run behaviour of a simulation | ⚠️ **Statistics, not trajectories** (§15 → `chaos-detection-control-applications-and-computation`) |

### 19.2 Sceptic's checklist for a chaos claim
- [ ] Is the system deterministic, bounded, and at least 3D (or a map)? (§1 → `chaos-foundations-dynamical-systems-and-bifurcations`, §2 → `chaos-foundations-dynamical-systems-and-bifurcations`)
- [ ] Is there a positive Lyapunov exponent, or just visual irregularity? (§6 → `chaos-logistic-map-lyapunov-and-attractors`)
- [ ] Was surrogate data testing done? ⚠️ **If not, assume coloured noise** (§12 → `chaos-detection-control-applications-and-computation`)
- [ ] Is the record long enough for the dimension claimed? (§12 → `chaos-detection-control-applications-and-computation`)
- [ ] Is the system stationary over the record? (§12 → `chaos-detection-control-applications-and-computation`)
- [ ] Is "chaos" doing mathematical work here, or is it a metaphor? (§14 → `chaos-detection-control-applications-and-computation`, §16)
- [ ] Is a causal claim being made from the butterfly effect? ⚠️ **That's the error** (§16.1)

---
