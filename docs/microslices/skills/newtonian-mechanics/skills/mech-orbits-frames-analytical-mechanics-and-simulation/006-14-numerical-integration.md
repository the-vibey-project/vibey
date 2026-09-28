---
id: skill-14-numerical-integration-b2f76e3ef8
purpose: 14 numerical integration
source: src/vibey_tools/skills/plugins/newtonian-mechanics/skills/mech-orbits-frames-analytical-mechanics-and-simulation/SKILL.md
requires: ["skill-13-chaos-and-the-limits-of-prediction-7cad17b655"]
links: []
---

## §14. Numerical Integration

**⚠️ The section that matters if you simulate any of this, and the failure mode is
specific and non-obvious.**

### 14.1 The methods
```
Explicit (forward) Euler    x += v·dt ; v += a·dt
  ⚠️ First order. SYSTEMATICALLY GAINS ENERGY in oscillatory systems. Orbits spiral out.
Implicit (backward) Euler
  ⚠️ Stable, but systematically LOSES energy. Orbits spiral in, springs die.
Semi-implicit (symplectic) Euler   v += a·dt ; x += v·dt    ⚠️ NOTE THE ORDER
  ⚠️ Same cost as explicit Euler, and it CONSERVES ENERGY on average. Nearly free win.
Velocity Verlet             second order, symplectic, time-reversible
  ⚠️ The standard for molecular dynamics and orbital mechanics
Leapfrog                    equivalent to Verlet, staggered
RK4                         ⚠️ Fourth order, very accurate per step, NOT symplectic —
                            energy drifts slowly over long runs
```

> **⚠️ GOTCHA — the most important numerical fact in classical simulation.** ⚠️ **Explicit
> Euler and semi-implicit Euler differ by the order of two lines of code, and that
> difference determines whether your simulation is stable over long times.**
> ```
> Explicit:       x_new = x + v*dt;  v_new = v + a(x)*dt      ⚠️ energy grows
> Semi-implicit:  v_new = v + a(x)*dt;  x_new = x + v_new*dt  ⚠️ energy bounded
> ```
> **Same operations, same cost, one uses the updated velocity.** ⚠️ **This is why game
> physics engines and orbital simulators use semi-implicit Euler or Verlet, and it is why
> a naive planet simulation spirals into the sun or off to infinity.**

### 14.2 Why symplectic matters
**⚠️ Symplectic integrators preserve the phase-space structure that §11's Hamiltonian
formulation describes** — Liouville's theorem. **They don't conserve energy exactly, but
the error oscillates within a bound rather than accumulating.**
⚠️ **The counterintuitive consequence**: **for long-duration simulation, a second-order
symplectic method (Verlet) beats fourth-order RK4**, because RK4's superior per-step
accuracy doesn't stop its energy from drifting monotonically. **Order of accuracy is the
wrong figure of merit for long integrations.**

### 14.3 Practical
**Timestep**: ⚠️ **must resolve the fastest timescale in the system** — the stiffest
spring, the closest orbital approach. **Adaptive stepping** for systems with wide dynamic
range (⚠️ **near-collision in gravitational N-body**).
**⚠️ Stiff systems** — where timescales differ by orders of magnitude — force impractically
small steps for explicit methods; **implicit methods are the answer despite their cost.**
**Constraints**: ⚠️ **stiff penalty springs are the naive approach and they make the system
stiff. Lagrange multipliers or projection methods (SHAKE/RATTLE) are the right ones.**
**Collision handling**: discrete detection **misses fast-moving thin objects (tunnelling)**
— ⚠️ **continuous collision detection or swept volumes.**
**⚠️ Always monitor a conserved quantity** — energy, momentum, angular momentum — **as a
correctness check. If it drifts, your integrator or timestep is wrong, and it's the
cheapest diagnostic you have.**
