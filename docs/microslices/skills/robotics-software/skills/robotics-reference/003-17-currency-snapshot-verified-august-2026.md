---
id: skill-17-currency-snapshot-verified-august-2026-41a96e5e78
purpose: 17 currency snapshot verified august 2026
source: src/vibey_tools/skills/plugins/robotics-software/skills/robotics-reference/SKILL.md
requires: ["skill-16-contested-questions-e9b03d7d84"]
links: ["skill-18-the-canon-c810504b12"]
---

## §17. Currency Snapshot — verified August 2026

**[DURABLE] §4–§7 → `robotics-stack-ros2-and-perception`, `robotics-planning-control-and-manipulation`'s theory, §11 → `robotics-safety-standards-and-deployment`'s real-time practice, and §12 → `robotics-safety-standards-and-deployment`'s testing discipline do not
move.** What follows is what does.

| Thing | Status as of Aug 2026 | Decay risk |
|---|---|---|
| **ROS 2 releases** | **One release each 23 May. Even years = LTS, 5 years support; odd years = 18 months.** **Lyrical Luth (May 2026, Ubuntu 26.04)** is current — Patch Release 2 on 2026/08/07. **Kilted Kaiju (May 2025)** supported to ~Nov/Dec 2026. **Jazzy Jalisco (May 2024, Ubuntu 24.04)** the production LTS, to 2029. **Humble** still patched (PR14, Feb 2026). **ROS 1 support ended May 2025** | Medium |
| **ROS 2 middleware** | ⚠️ **Kilted was the first release with Eclipse Zenoh as Tier 1 middleware** (Zenoh 1.0), expected **more efficient and secure than DDS**, particularly for universities and complex network environments. Options: Fast DDS (default; **`fastrtps` renamed `fastdds`**), Cyclone DDS, RTI Connext (7.3.0; ⚠️ **Connext Micro RMW deprecated in Kilted, removal planned**). Kilted also brought OpenCV 4.12 native support, rosbag2 recorder/player as rclcpp components, and **`ament_target_dependencies()` deprecation**. Recommended Gazebo for Kilted: **Ionic** | Medium |
| **⚠️ ISO 10218:2025** | **Parts 1 and 2 published Feb 2025, in force 1 April 2025** — first revision since 2011, ~8 years of work across 20+ countries. ⚠️ **ISO/TS 15066 absorbed into Part 2 — no standalone cobot standard.** ⚠️ **The terms "collaborative robot" and "collaborative operation" removed — collaboration is a property of the application, not the robot.** Added: **explicit functional safety**, **robot classification (Class I/II)**, ⚠️ **cybersecurity requirements**, EOAT and manual load/unload guidance. **Part 2 nearly tripled in length.** Adopted as **ANSI/A3 R15.06-2025** and CSA Z434 | Low |
| **Enforceability** | ISO standards voluntary in themselves; binding via contract and harmonisation. ⚠️ **EU Machinery Regulation 2023/1230 applies from 20 January 2027.** US pressure via OSHA penalties | Medium |
| **⚠️ Humanoid standards gap** | The 2025 revision **explicitly leaves gaps on AI, humanoids, and mobile manipulation.** **ISO 25785-1 under development for dynamically stable robots.** Humanoid-specific hazards — fall zones, dynamic balance, energy-dense hot-swap batteries — **not covered by arm-derived contact-force models** | **High** |
| **⚠️ VLA frontier** | **π₀ / π₀.₅ / π₀.₇** (Physical Intelligence; π₀.₅ targets open-world generalization). **Gemini Robotics / 1.5** (DeepMind) — "thinking before acting," embodied reasoning, **motion transfer**; on-device variant adapts with **50–100 demonstrations**, trained primarily on ALOHA and adapted to bi-arm Franka FR3 and Apptronik Apollo; **trusted-tester availability, not general release**. **GR00T N-series** (NVIDIA) — ⚠️ **dual-system: VLM System 2 + diffusion-transformer System 1 at 120Hz, jointly trained**; **N1.7 at General Availability, Apache 2.0**, Cosmos-Reason2-2B/Qwen3-VL backbone; adopters include AeiRobot, Foxlink, NEURA, Lightwheel. **Helix** (Figure) uses a 7B VLM hierarchically | **High** |
| **VLA architecture constraint** | ⚠️ **π₀ and GR00T N1 both ~2B-parameter backbones — small models required for on-device inference and real-time latency.** Hierarchical designs run a larger VLM at lower frequency. Cloud-hosted (Gemini Robotics) trades latency and connectivity | **High** |
| **Data and world models** | **Open X-Embodiment / RT-X** and **DROID** the reference cross-embodiment datasets. **NVIDIA Cosmos** generates synthetic trajectories (GR00T-Dreams blueprint: vast trajectory data **from a single image and language instruction**). **World-action models** — pretrain to imagine, fine-tune to act — an active 2026 direction. Open models: OpenVLA, RDT-1B, X-VLA, **LingBot-VLA (Ant Group, 20K hours real dual-arm data, open-sourced)**, Xiaomi-Robotics-0 | **High** |

**Goes stale fastest:** §8 → `robotics-learning-simulation-and-fleets` and §17's VLA rows — assume monthly movement. **Essentially
never stale:** §3.4 → `robotics-stack-ros2-and-perception`, §4 → `robotics-stack-ros2-and-perception`, §5 → `robotics-planning-control-and-manipulation`, §6 → `robotics-planning-control-and-manipulation`, §7 → `robotics-planning-control-and-manipulation`, §11 → `robotics-safety-standards-and-deployment`, §12 → `robotics-safety-standards-and-deployment`, §15.

---
