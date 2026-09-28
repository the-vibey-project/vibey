---
id: skill-15-anti-patterns-87eeba3c05
purpose: 15 anti patterns
source: src/vibey_tools/skills/plugins/robotics-software/skills/robotics-reference/SKILL.md
requires: []
links: ["skill-16-contested-questions-e9b03d7d84"]
---

## §15. Anti-Patterns

| Anti-pattern | Why |
|---|---|
| Debugging the algorithm before checking transforms and timestamps | ⚠️ **The most common robotics bug, by a wide margin** (§3.4 → `robotics-stack-ros2-and-perception`) |
| Mixing coordinate frames by hand | Produces plausible wrong behaviour, not errors (§3.4 → `robotics-stack-ros2-and-perception`) |
| Ignoring quaternion ordering conventions | (x,y,z,w) in ROS, (w,x,y,z) elsewhere (§3.4 → `robotics-stack-ros2-and-perception`) |
| Timestamping at publish rather than measurement | Corrupts every downstream filter (§3.4 → `robotics-stack-ros2-and-perception`) |
| Unsynchronized clocks across compute nodes | Fusion silently degrades (§3.4 → `robotics-stack-ros2-and-perception`) |
| Not budgeting end-to-end latency | ⚠️ **Dead time destabilizes controllers** (§6.2 → `robotics-planning-control-and-manipulation`) |
| Optimizing average latency, ignoring jitter | ⚠️ **Determinism beats speed** (§6.2 → `robotics-planning-control-and-manipulation`, §11 → `robotics-safety-standards-and-deployment`) |
| Two cameras and calling it redundancy | Correlated failure modes (§3 → `robotics-stack-ros2-and-perception`) |
| Trusting wheel odometry | It lies confidently under slip (§3 → `robotics-stack-ros2-and-perception`) |
| Treating an IMU as an absolute sensor | It drifts. Always (§3 → `robotics-stack-ros2-and-perception`) |
| Planning without kinodynamic constraints | Plans the robot can't execute (§5 → `robotics-planning-control-and-manipulation`) |
| Potential fields for anything nontrivial | Local minima; everyone rediscovers this (§5 → `robotics-planning-control-and-manipulation`) |
| No integral windup clamping | Saturation → windup → overshoot (§6.2 → `robotics-planning-control-and-manipulation`) |
| Allocation, logging, or unbounded loops in the control path | ⚠️ **Destroys determinism** (§11 → `robotics-safety-standards-and-deployment`) |
| Safety logic inside the application controller | ⚠️ **Must be an independent rated layer** (§13.3 → `robotics-safety-standards-and-deployment`) |
| A watchdog that depends on the software it watches | Not a watchdog (§11 → `robotics-safety-standards-and-deployment`) |
| "We bought a collaborative robot, so it's safe" | ⚠️ **ISO 10218:2025 removed the term — safety is a property of the application** (§13.1 → `robotics-safety-standards-and-deployment`) |
| Citing ISO/TS 15066 as a standalone standard | ⚠️ **Absorbed into ISO 10218-2:2025** (§13.1 → `robotics-safety-standards-and-deployment`) |
| Deploying humanoids against arm-shaped safety standards | ⚠️ **The gap is real and it's yours** (§13.2 → `robotics-safety-standards-and-deployment`) |
| Learned policy with no classical safety layer beneath | No safety case is possible (§8.3 → `robotics-learning-simulation-and-fleets`, §13 → `robotics-safety-standards-and-deployment`) |
| Sim-only validation | Ships things that only work in sim (§9 → `robotics-learning-simulation-and-fleets`) |
| Domain randomization that omits latency | Under-done and disproportionately costly (§9 → `robotics-learning-simulation-and-fleets`) |
| Not recording every run | ⚠️ **An unrecorded failure may be unreproducible** (§12 → `robotics-safety-standards-and-deployment`) |
| No deterministic replay capability | The most valuable debugging tool, absent (§12 → `robotics-safety-standards-and-deployment`) |
| Skipping hardware-in-the-loop | The most under-invested test rung (§12 → `robotics-safety-standards-and-deployment`) |
| No defined behaviour on fleet-manager disconnect | The actuators keep moving during a partition (§10 → `robotics-learning-simulation-and-fleets`) |
| OTA update with no staged rollout or rollback | You can brick a fleet (§10 → `robotics-learning-simulation-and-fleets`) |
| ROS 2 QoS mismatch | ⚠️ **Silently no connection, no error** (§2.3 → `robotics-stack-ros2-and-perception`) |
| Default single-threaded executor for timing-sensitive work | Unpredictable callback scheduling (§2.3 → `robotics-stack-ros2-and-perception`) |
| Assuming ROS 2 is real-time out of the box | It is not (§2.3 → `robotics-stack-ros2-and-perception`, §11 → `robotics-safety-standards-and-deployment`) |
| Multicast DDS discovery on a large fleet network | Floods; use discovery servers or Zenoh (§2.3 → `robotics-stack-ros2-and-perception`) |
| Targeting a non-LTS ROS distro for production | 18 months of support (§2.2 → `robotics-stack-ros2-and-perception`) |
| Quoting VLA benchmark numbers as deployment readiness | ⚠️ **Evaluation transfers poorly** (§8.3 → `robotics-learning-simulation-and-fleets`) |

---
