---
id: skill-13-chaos-and-the-limits-of-prediction-7cad17b655
purpose: 13 chaos and the limits of prediction
source: src/vibey_tools/skills/plugins/newtonian-mechanics/skills/mech-orbits-frames-analytical-mechanics-and-simulation/SKILL.md
requires: ["skill-12-fluids-and-continuous-media-briefly-000b91a9ec"]
links: ["skill-14-numerical-integration-b2f76e3ef8"]
---

## §13. Chaos and the Limits of Prediction

**⚠️ Newtonian mechanics is deterministic. It is not predictable. These are different
claims and conflating them is a real error.**

**Sensitive dependence on initial conditions**: nearby trajectories diverge exponentially,
at a rate set by the **Lyapunov exponent**. ⚠️ **Since you never know initial conditions
exactly, prediction has a horizon** — and **improving your measurements buys you only
logarithmic improvement in that horizon.** **Ten times better data gets you a modest
constant more time, not ten times more.**

**⚠️ Chaos requires nonlinearity and at least three dimensions in a continuous autonomous
system.** Examples: the **double pendulum** (⚠️ **the canonical demonstration, and
genuinely chaotic despite being a two-body problem**), the **three-body problem**
(⚠️ **no general closed-form solution — Poincaré, 1890, and this is where chaos was
discovered**), driven oscillators, and weather.

**⚠️ KAM theory** — the useful counterweight: **under small perturbations, many quasi-
periodic orbits survive rather than dissolving into chaos.** **The solar system is not
obviously stable and not obviously chaotic; its long-term behaviour is a live research
question.**

---
