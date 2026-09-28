---
id: skill-14-guidance-and-control-c3e724f2f2
purpose: 14 guidance and control
source: src/vibey_tools/skills/plugins/military-space-rockets-and-fusion/skills/endeavour-orbits-ascent-structures-and-reentry/SKILL.md
requires: ["skill-13-aerodynamic-loads-and-thin-walled-structures-06799f35c8"]
links: ["skill-15-reentry-physics-c14a072dcf"]
---

## §14 Guidance and control

Attitude dynamics:

    I·ω̇ + ω × (I·ω) = M

The **ω × Iω gyroscopic coupling term is why 3-axis control is not three independent problems** — an
axis you excite shows up in the others.

**TVC control authority is small and shrinking:** typical gimbal range is **only ±5–8°**, and it
**decreases as propellant depletes and the centre of mass moves**.

Two control challenges, each a real loss-of-vehicle mode:

- **Slosh** — propellant in a partly-full tank behaves like a pendulum; **anti-slosh baffles raise
  damping**.
- **Flexible body modes** — the vehicle bends, the IMU measures local attitude *including* the bending
  mode, and a controller with gain at that frequency **drives the mode**. **Notch filters at the
  bending frequencies are mandatory**, and because **the frequencies shift as propellant drains, the
  filters must be scheduled**.

### Guidance phases

| Phase | Law | Why |
|---|---|---|
| Atmospheric | **open-loop pitch program** | closed-loop steering at high q risks commanding an α the structure cannot survive (§13 above) |
| Vacuum | **Powered Explicit Guidance** | solves the **linear-tangent steering law**, which is the optimal-control solution |

**Powered descent** is the hard one: the landing problem is **non-convex**, because thrust magnitude is
**bounded below by a non-zero minimum** — an engine cannot be throttled to nothing and restarted at
will.

> **LOSSLESS CONVEXIFICATION IS THE GENUINELY IMPORTANT MODERN CONTRIBUTION.** Açıkmeşe and Ploen
> proved that a **relaxed convex formulation has the same optimum** as the original non-convex problem.
> That makes **real-time solutions with guaranteed convergence** possible, and it is **why autonomous
> propulsive landing became practical** — a theorem, not an incremental engineering gain.
