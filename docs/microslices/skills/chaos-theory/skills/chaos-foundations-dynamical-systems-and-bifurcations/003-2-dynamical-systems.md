---
id: skill-2-dynamical-systems-bc9348511c
purpose: 2 dynamical systems
source: src/vibey_tools/skills/plugins/chaos-theory/skills/chaos-foundations-dynamical-systems-and-bifurcations/SKILL.md
requires: ["skill-1-what-chaos-is-d3df5c872f"]
links: ["skill-3-stability-and-linearization-6e637cca70"]
---

## §2. Dynamical Systems

**State space (phase space)** — each axis a state variable; a point is a complete
instantaneous state; a trajectory is the system's history.
```
Continuous (flows):   dx/dt = f(x)         ODEs
Discrete (maps):      x_{n+1} = f(x_n)     iterated maps
```
**Autonomous** (no explicit `t`) vs **non-autonomous** (⚠️ **a driven system; you can make
it autonomous by adding time as a state variable, which raises the dimension and is why
driven 2D systems can be chaotic**).

**Attractors** — where trajectories settle:
```
Fixed point       steady state
Limit cycle       ⚠️ self-sustained periodic oscillation, isolated
Torus (quasi-periodic)  two or more incommensurate frequencies
STRANGE ATTRACTOR ⚠️ fractal geometry, chaotic dynamics
```
**Basin of attraction** — the set of initial conditions leading to a given attractor.
⚠️ **Basin boundaries can themselves be fractal, which means arbitrarily small uncertainty
in initial conditions leaves you unable to say which attractor you'll reach — a second,
distinct kind of unpredictability.**

**⚠️ The Poincaré-Bendixson theorem is the key dimensional constraint**: in a **continuous,
autonomous system**, a bounded trajectory in **two dimensions** must approach a fixed point
or a limit cycle. **Chaos is impossible.**
> **⚠️ GOTCHA — you need at least THREE dimensions for chaos in a continuous autonomous
> system.** ⚠️ **This is why the Lorenz system has exactly three variables — it's the
> minimum.** **But discrete maps can be chaotic in ONE dimension** (the logistic map, §5 → `chaos-logistic-map-lyapunov-and-attractors`),
> **because iteration doesn't have the topological constraint that continuous trajectories
> do — a map can jump, a flow cannot cross itself.**

---
