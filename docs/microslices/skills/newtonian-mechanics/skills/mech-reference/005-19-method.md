---
id: skill-19-method-0aeee88144
purpose: 19 method
source: src/vibey_tools/skills/plugins/newtonian-mechanics/skills/mech-reference/SKILL.md
requires: ["skill-18-quick-reference-843615e472"]
links: []
---

## §19. Method

**No searches were run, and none could have been useful.** ⚠️ **This is settled physics
and has been for centuries**: Newton's *Principia* (1687), Euler's rigid-body work
(1750s), Lagrange's *Mécanique analytique* (1788), Hamilton (1833), Noether (1918),
Poincaré on the three-body problem (1890). **Nothing in §1–§13 → `mech-kinematics-newtons-laws-and-forces`, `mech-energy-momentum-and-collisions`, `mech-rotation-rigid-bodies-and-oscillations`, `mech-orbits-frames-analytical-mechanics-and-simulation` has changed or will
change.**

**Sources** are the standard texts in §17 — chiefly **Kleppner & Kolenkow** and **Morin**
for the core, **Taylor** and **Landau & Lifshitz** for §11 → `mech-orbits-frames-analytical-mechanics-and-simulation`, **Strogatz** for §13 → `mech-orbits-frames-analytical-mechanics-and-simulation`, and
**Hairer/Lubich/Wanner** for §14 → `mech-orbits-frames-analytical-mechanics-and-simulation`'s geometric integration results.

**Scoped to complement**: relativity, quantum mechanics, and the boundaries where
classical mechanics fails belong in a fundamental-physics reference; ⚠️ **this document
stays inside the classical domain deliberately and says where the edges are (§9 → `mech-orbits-frames-analytical-mechanics-and-simulation`'s
perihelion precession, §12 → `mech-orbits-frames-analytical-mechanics-and-simulation`'s turbulence) rather than crossing them.** Rocket propulsion and
the variable-mass derivation gestured at in §2.1 → `mech-kinematics-newtons-laws-and-forces` sit in a rocket-science reference.

**Confidence: high throughout**, with one distinction worth drawing.

**§1–§13 → `mech-kinematics-newtons-laws-and-forces`, `mech-energy-momentum-and-collisions`, `mech-rotation-rigid-bodies-and-oscillations`, `mech-orbits-frames-analytical-mechanics-and-simulation` are textbook results stated with their validity conditions** — ⚠️ **and the
conditions are the valuable part, because essentially every error in classical mechanics
is a correct formula applied outside its assumptions.** Constant-acceleration kinematics
with non-constant acceleration, `N = mg` on an incline, small-angle pendulum period at
large amplitude, Bernoulli off a streamline: **the formula is right and the application is
wrong.** §15 collects these.

**§15's misconception list is grounded in physics-education research**, principally the
**Force Concept Inventory** literature — ⚠️ **these are documented, measured, and
resistant to instruction, not anecdotes about students.**

⚠️ **Two specific corrections I've made deliberately against widespread belief, both of
which you will find stated the other way in reputable places.** **The Tacoma Narrows
collapse is attributed in the modern engineering literature to aeroelastic flutter — a
self-excited feedback instability — not to simple resonance**, and it remains the standard
textbook resonance example anyway. **And the Coriolis-bathtub claim is off by orders of
magnitude** while being one of the most-repeated pieces of physics folklore.

**§14 → `mech-orbits-frames-analytical-mechanics-and-simulation` is the section I'd most encourage reading if you write simulations**, and ⚠️ **its
central claim is counterintuitive enough to state plainly: for long integrations, a
second-order symplectic method beats fourth-order RK4.** **Order of accuracy is the wrong
figure of merit when what you care about is qualitative long-run behaviour rather than
per-step error.**
