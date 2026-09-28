---
id: skill-19-quick-reference-c1c93840e1
purpose: 19 quick reference
source: src/vibey_tools/skills/plugins/robotics-software/skills/robotics-reference/SKILL.md
requires: ["skill-18-the-canon-c810504b12"]
links: ["skill-20-sources-and-method-f462f6af9c"]
---

## §19. Quick Reference

### 19.1 Picking the tool
| Need | Use |
|---|---|
| Middleware for a new production robot | **ROS 2 Jazzy (LTS)**; Zenoh or Cyclone DDS (§2 → `robotics-stack-ros2-and-perception`) |
| Hard real-time control loop | ⚠️ **Not ROS. PREEMPT_RT or an RTOS, isolated core** (§11 → `robotics-safety-standards-and-deployment`) |
| Navigation stack | Nav2 (§5 → `robotics-planning-control-and-manipulation`) |
| Arm motion planning | MoveIt 2 + OMPL (§5 → `robotics-planning-control-and-manipulation`) |
| Trajectory optimization | Drake, iLQR, or a QP-based MPC (§6 → `robotics-planning-control-and-manipulation`) |
| Contact-rich control | Impedance/admittance control (§6 → `robotics-planning-control-and-manipulation`) |
| Legged locomotion | MPC + whole-body control, or RL trained in Isaac Lab (§6 → `robotics-planning-control-and-manipulation`, §8 → `robotics-learning-simulation-and-fleets`) |
| SLAM, LiDAR | FAST-LIO2 / KISS-ICP (§4 → `robotics-stack-ros2-and-perception`) |
| SLAM, visual-inertial | VINS-Fusion / ORB-SLAM3 (§4 → `robotics-stack-ros2-and-perception`) |
| Pose graph back-end | GTSAM or Ceres (§4 → `robotics-stack-ros2-and-perception`) |
| RL training at scale | Isaac Lab (§9 → `robotics-learning-simulation-and-fleets`) |
| Contact-accurate research sim | MuJoCo or Drake (§9 → `robotics-learning-simulation-and-fleets`) |
| Manipulation policy from demos | Diffusion policy; or fine-tune a VLA (§8 → `robotics-learning-simulation-and-fleets`) |
| Generalist manipulation baseline | GR00T N1.7 (Apache 2.0) or OpenVLA (§8 → `robotics-learning-simulation-and-fleets`) |
| Log inspection and visualization | Foxglove (§12 → `robotics-safety-standards-and-deployment`) |
| Fleet interop | Open-RMF (§10 → `robotics-learning-simulation-and-fleets`) |

### 19.2 When the robot misbehaves
1. **Check the transform tree.** Frames right? (§3.4 → `robotics-stack-ros2-and-perception`)
2. **Check timestamps and clock sync.** (§3.4 → `robotics-stack-ros2-and-perception`)
3. **Check end-to-end latency** and its jitter. (§6.2 → `robotics-planning-control-and-manipulation`)
4. **Check QoS** — is the topic actually connected? (§2.3 → `robotics-stack-ros2-and-perception`)
5. **Visualize the perception output.** Does it see what you think? (§12 → `robotics-safety-standards-and-deployment`)
6. **Replay the bag** with the suspect layer isolated. (§12 → `robotics-safety-standards-and-deployment`)
7. **Check for saturation and windup** in the controller. (§6.2 → `robotics-planning-control-and-manipulation`)
8. **Then** consider the algorithm.

### 19.3 Facts worth holding
- **Control 100Hz–10kHz; estimation 50–500Hz; perception 10–60Hz; planning 1–10Hz.**
- **Sample at 10–20× your control bandwidth.**
- ⚠️ **Jitter is worse than latency.**
- **REP-103: x-forward, y-left, z-up.** ROS quaternions are **(x,y,z,w)**.
- **ISO/TS 15066 no longer stands alone** — it's inside ISO 10218-2:2025.
- ⚠️ **"Collaborative" describes the application, not the robot.**
- **EU Machinery Regulation 2023/1230 applies 20 January 2027.**
- **GR00T: System 2 VLM plans, System 1 diffusion transformer acts at 120Hz.**
- **VLA backbones ~2B parameters** — latency, not capability, sets the ceiling.

---
