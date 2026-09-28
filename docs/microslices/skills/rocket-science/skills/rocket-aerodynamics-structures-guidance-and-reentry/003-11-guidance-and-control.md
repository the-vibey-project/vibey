---
id: skill-11-guidance-and-control-dec9815c71
purpose: 11 guidance and control
source: src/vibey_tools/skills/plugins/rocket-science/skills/rocket-aerodynamics-structures-guidance-and-reentry/SKILL.md
requires: ["skill-10-structures-df4fb486f4"]
links: ["skill-12-reentry-physics-cc017e9e2d"]
---

## §11. Guidance and Control

**Attitude dynamics** — Euler's equations for a rigid body:
```
I·ω̇ + ω × (I·ω) = M
```
⚠️ **The `ω × Iω` gyroscopic coupling term is why 3-axis control isn't three independent
problems.**

**TVC control authority**: a gimbal deflection δ produces moment `M = F·L·sin δ` where L is
the distance from gimbal to CoM. ⚠️ **Typical gimbal range is only ±5–8°** — control
authority is limited, and it decreases as propellant depletes and the CoM moves.

**Control challenges, and each is a real loss-of-vehicle mode:**
- **⚠️ Slosh**: propellant in a partly-full tank behaves like a pendulum with a natural
  frequency `ω_s ≈ √(1.84·g_eff/R)`. If it couples with the control loop, divergence.
  **Anti-slosh baffles** raise damping.
- **⚠️ Flexible body modes**: the vehicle bends. **The IMU measures local attitude including
  the bending mode.** If the controller has gain at that frequency, it drives the mode.
  **Notch filters at the bending frequencies** are mandatory — and the frequencies shift as
  propellant drains, so the filters must be scheduled.
- **Actuator lag and rate limits.**

**Guidance**:
- **Atmospheric phase**: ⚠️ **open-loop pitch program.** Closed-loop steering at high `q`
  risks commanding an α the structure can't survive — the guidance is deliberately dumb
  while it matters.
- **Vacuum phase**: **Powered Explicit Guidance (PEG)** / **iterative guidance mode** —
  solves the linear-tangent steering law that is the optimal-control solution for a flat,
  constant-gravity field, re-solved each cycle.
- **Optimal control formally**: minimize propellant subject to dynamics → Pontryagin's
  maximum principle gives **bang-bang thrust** and the **primer vector** determining
  optimal burn timing.
- **⚠️ Powered descent**: the landing problem is non-convex (thrust magnitude bounded below
  by a non-zero minimum). **Lossless convexification** (Açıkmeşe & Ploen) proves that a
  relaxed convex formulation has the same optimum — **making a real-time, guaranteed-
  convergence solution possible.** This is the genuinely important modern contribution to
  the field, and it's why autonomous propulsive landing became practical.

⚠️ **The "hoverslam"**: if minimum throttle produces T/W > 1, hovering is impossible. The
burn must be timed so velocity and altitude reach zero simultaneously — **a boundary-value
problem with no margin for a late start.**

**Navigation**: strapdown IMU integration accumulates error as roughly `t³` in position for
a bias error. Bounded by GNSS, star trackers, or radar altimetry, fused via Kalman filter.

---
