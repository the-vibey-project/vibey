---
id: skill-15-misconceptions-the-consolidated-list-1ef3e846c0
purpose: 15 misconceptions the consolidated list
source: src/vibey_tools/skills/plugins/newtonian-mechanics/skills/mech-reference/SKILL.md
requires: []
links: ["skill-16-numbers-and-formulas-6e3e616848"]
---

## §15. Misconceptions — the consolidated list

| Misconception | The correction |
|---|---|
| Motion requires a force | ⚠️ **Constant velocity requires ZERO net force** (§2.2 → `mech-kinematics-newtons-laws-and-forces`) |
| A thrown object carries a forward force | ⚠️ **It carries momentum. Only gravity and drag act** (§2.2 → `mech-kinematics-newtons-laws-and-forces`) |
| Third-law pairs cancel | ⚠️ **Different bodies. Nothing would ever accelerate** (§2.2 → `mech-kinematics-newtons-laws-and-forces`) |
| Heavier objects fall faster | Not in vacuum; in air it's the mass/drag ratio (§2.2 → `mech-kinematics-newtons-laws-and-forces`) |
| Centrifugal force pushes you outward | ⚠️ **Only exists in the rotating frame** (§2.2 → `mech-kinematics-newtons-laws-and-forces`, §10 → `mech-orbits-frames-analytical-mechanics-and-simulation`) |
| N = mg always | ⚠️ **Only in one special case** (§3.2 → `mech-kinematics-newtons-laws-and-forces`) |
| Static friction = μ_s N | ⚠️ **It's an inequality. Compute from equilibrium** (§3.3 → `mech-kinematics-newtons-laws-and-forces`) |
| Friction depends on contact area | Not in the Coulomb model, for good reason (§3.3 → `mech-kinematics-newtons-laws-and-forces`) |
| Constant-acceleration equations always apply | ⚠️ **Only for constant acceleration** (§1 → `mech-kinematics-newtons-laws-and-forces`) |
| Zero velocity means zero acceleration | Top of the arc (§1 → `mech-kinematics-newtons-laws-and-forces`) |
| Energy is "lost" to friction | ⚠️ **It becomes thermal energy. Never lost** (§4 → `mech-energy-momentum-and-collisions`) |
| Moment of inertia is a property of the object | ⚠️ **Of the object AND the axis** (§6 → `mech-rotation-rigid-bodies-and-oscillations`) |
| L and ω are parallel | ⚠️ **Only about principal axes** (§7 → `mech-rotation-rigid-bodies-and-oscillations`) |
| Pendulum period is amplitude-independent | ⚠️ **Only in the small-angle approximation** (§8 → `mech-rotation-rigid-bodies-and-oscillations`) |
| Tacoma Narrows was resonance | ⚠️ **Aeroelastic flutter — a self-excited instability** (§8 → `mech-rotation-rigid-bodies-and-oscillations`) |
| Coriolis determines bathtub drains | ⚠️ **Orders of magnitude too small** (§10 → `mech-orbits-frames-analytical-mechanics-and-simulation`) |
| Bernoulli explains lift via equal transit time | ⚠️ **Wrong, and universally repeated** (§12 → `mech-orbits-frames-analytical-mechanics-and-simulation`) |
| Deterministic means predictable | ⚠️ **Chaos separates them** (§13 → `mech-orbits-frames-analytical-mechanics-and-simulation`) |
| RK4 is best because it's fourth order | ⚠️ **Not for long integrations. Symplectic wins** (§14.2 → `mech-orbits-frames-analytical-mechanics-and-simulation`) |
| Euler integration is fine for orbits | ⚠️ **It spirals. Reorder two lines** (§14.1 → `mech-orbits-frames-analytical-mechanics-and-simulation`) |
| F = ma works for rockets | ⚠️ **Variable mass needs F = dp/dt done properly** (§2.1 → `mech-kinematics-newtons-laws-and-forces`) |

---
