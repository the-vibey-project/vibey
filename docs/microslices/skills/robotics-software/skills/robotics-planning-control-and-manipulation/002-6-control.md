---
id: skill-6-control-c97f2c17a7
purpose: 6 control
source: src/vibey_tools/skills/plugins/robotics-software/skills/robotics-planning-control-and-manipulation/SKILL.md
requires: ["skill-5-motion-planning-9a936cfa40"]
links: ["skill-7-manipulation-59df12bd8e"]
---

## §6. Control

**[DURABLE] The most durable body of theory in this document. None of it has changed in
decades and none of it will.**

### 6.1 The ladder

| Controller | Use | ⚠️ Watch |
|---|---|---|
| **PID** | ⚠️ **Still the workhorse of industrial robotics** | Integral windup; derivative noise amplification; **needs retuning as the plant changes** |
| **Feedforward + feedback** | ⚠️ **The single biggest practical improvement over pure PID** — model what you can, correct the rest | Requires a model |
| **LQR** | Optimal for linear systems with quadratic cost | Linear assumption |
| **iLQR / DDP** | Nonlinear trajectory optimization | Local |
| **MPC** | ⚠️ **Handles constraints explicitly, and that's why it won** — the standard for AVs, legged robots, and drones | Compute cost; needs a good model and a solver that hits the deadline |
| **Impedance / admittance** | ⚠️ **Contact tasks.** Controls the *relationship* between force and motion rather than either alone | Stability at stiff contact |
| **Whole-body control** | Humanoids and legged systems — hierarchical QP over all joints subject to balance and contact constraints | Serious complexity |
| **Adaptive / robust (H∞, sliding mode)** | Uncertain or varying plants | Chatter; conservatism |
| **Learned policies** | §8 → `robotics-learning-simulation-and-fleets` | ⚠️ **No stability guarantees** |

### 6.2 What actually matters in practice

**[DURABLE] The system-level facts that dominate controller performance:**
- **⚠️ Latency and dead time destabilize.** Every millisecond between measurement and
  actuation reduces achievable bandwidth. **This is why §3.4 → `robotics-stack-ros2-and-perception` matters to §6.**
- **Jitter is worse than latency.** A consistent 5ms delay can be compensated; a delay
  varying 1–20ms cannot. ⚠️ **Determinism beats speed** (§11 → `robotics-safety-standards-and-deployment`).
- **Actuator saturation** invalidates your linear analysis, and **integral windup is what
  happens next.** Clamp it.
- **Discretization**: your continuous-time design is running at a finite rate.
  ⚠️ **Sample at least 10–20× your bandwidth of interest.**
- **Backlash, friction, and compliance** are what separate the model from the machine.
  Stiction in particular is nonlinear and nasty.
- **⚠️ Series-elastic and torque-controlled actuators changed what's possible** in legged
  and contact-rich robotics — they make force controllable rather than merely position.
- **Safety limits belong in a separate layer** that can't be argued with by the controller
  (§13 → `robotics-safety-standards-and-deployment`).

---
