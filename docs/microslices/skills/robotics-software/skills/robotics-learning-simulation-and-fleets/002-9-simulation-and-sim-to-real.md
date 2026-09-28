---
id: skill-9-simulation-and-sim-to-real-42fee9aa6e
purpose: 9 simulation and sim to real
source: src/vibey_tools/skills/plugins/robotics-software/skills/robotics-learning-simulation-and-fleets/SKILL.md
requires: ["skill-8-the-learning-layer-1149b8d707"]
links: ["skill-10-multi-robot-and-fleets-7933322c6d"]
---

## §9. Simulation and Sim-to-Real

**[DURABLE] Simulation is not optional at this point** — it's where RL training, CI,
regression testing, and scenario coverage happen.

| Simulator | Position |
|---|---|
| **Isaac Sim / Isaac Lab** | ⚠️ **GPU-parallel, photorealistic, the RL training standard.** NVIDIA-coupled |
| **MuJoCo** | ⚠️ **Fast, accurate contact dynamics, now free and open.** The research default for manipulation and locomotion |
| **Gazebo** (Harmonic/Ionic) | ROS-native, general-purpose. Ionic is the recommended pairing for Kilted |
| **PyBullet** | Lightweight, accessible, widely used in research |
| **Drake** (TRI) | ⚠️ **Rigorous multibody dynamics and optimization**; strong on contact and verification |
| **CARLA / AWSIM** | Autonomous driving |
| **Genesis, Newton** | Newer generative/differentiable physics efforts |

> **⚠️ GOTCHA — the sim-to-real gap, which is the field's permanent tax.** Simulators get
> **contact, friction, deformables, and sensor noise wrong**, and those are exactly the
> things that matter. **The mitigations that work**:
> - **Domain randomization** — randomize masses, friction, latencies, textures, and
>   lighting so the policy can't overfit to sim's specifics. ⚠️ **Randomizing *latency* is
>   under-done and disproportionately valuable.**
> - **System identification** — measure your actual robot's parameters and put them in the
>   sim.
> - **Sim-to-real-to-sim** — use real rollouts to correct the simulator.
> - **⚠️ Keep a real-hardware regression suite.** Sim-only validation always eventually
>   ships something that only works in sim.

---
