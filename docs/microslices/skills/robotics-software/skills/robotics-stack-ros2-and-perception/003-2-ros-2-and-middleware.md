---
id: skill-2-ros-2-and-middleware-22e45f3041
purpose: 2 ros 2 and middleware
source: src/vibey_tools/skills/plugins/robotics-software/skills/robotics-stack-ros2-and-perception/SKILL.md
requires: ["skill-1-the-stack-1b347a9e06"]
links: ["skill-3-perception-0ad064825f"]
---

## §2. ROS 2 and Middleware

### 2.1 What ROS actually is

**[DURABLE] Despite the name, ROS is not an operating system** — it's an SDK plus a
middleware plus a package ecosystem. **The value was never the message passing; it's that
thousands of drivers, algorithms, and tools speak the same interfaces.**

**⚠️ The ROS 1 → ROS 2 change that matters**: ROS 1 had a **central `rosmaster`** — a
single point of failure with custom TCP/UDP transports, no security, and no real-time
guarantees. **ROS 2 has no master**; discovery is distributed via **DDS**, the
publish-subscribe standard used in aerospace and defence. **ROS 1 support ended May 2025.
New work is ROS 2, without qualification.**

### 2.2 [VERSIONED] The distributions

**Release cadence: one release every year on 23 May.** **Even years are LTS with five
years of support; odd years get 18 months.** Each release targets exactly one Ubuntu LTS.

| Distro | Status |
|---|---|
| **Lyrical Luth** (May 2026) | ⚠️ **Current release**, on Ubuntu 26.04. Patch releases through 2026 |
| **Kilted Kaiju** (May 2025) | Supported to **~Nov/Dec 2026**. First release with **Zenoh as Tier 1 middleware** |
| **Jazzy Jalisco** (May 2024) | ⚠️ **The LTS most production systems are on** — supported to 2029, Ubuntu 24.04 |
| **Humble Hawksbill** (2022) | Still patched (Patch Release 14, Feb 2026); Ubuntu 22.04 |

**[DURABLE] For production, target the LTS.** Jazzy today; the next LTS lands May 2028.

### 2.3 The middleware layer

**RMW implementations** are pluggable: **Fast DDS** (default; ⚠️ **note `fastrtps` was
renamed `fastdds` in Kilted**), **Cyclone DDS** (⚠️ **widely preferred for reliability and
simplicity**), **RTI Connext** (commercial, aerospace/defence pedigree, safety-certified
variants), and **Zenoh** — ⚠️ **a genuine shift: Tier 1 from Kilted, expected to be more
efficient and more secure than DDS, and notably better across complex network
environments** where DDS multicast discovery struggles.

> **⚠️ GOTCHA — the ROS 2 problems that bite in production:**
> - **DDS discovery on large networks.** ⚠️ **Multicast discovery floods, and it's the
>   most common "why is my robot fleet slow" cause.** Use discovery servers, or Zenoh.
> - **QoS profile mismatches.** ⚠️ **Publisher and subscriber with incompatible QoS
>   silently don't connect** — no error, just no data. Check `ros2 topic info -v` first.
> - **Executor behaviour.** The default single-threaded executor gives you unpredictable
>   callback scheduling. **For anything timing-sensitive, use multi-threaded or
>   real-time executors and set thread priorities deliberately.**
> - **ROS 2 is not real-time by itself.** §11 → `robotics-safety-standards-and-deployment`.
> - **Serialization cost.** Use intra-process communication and zero-copy for
>   high-bandwidth topics (camera, point cloud) or you'll burn CPU on copies.
> - **`ament_target_dependencies()` is deprecated** in favour of modern CMake targets.

### 2.4 The rest of the ecosystem and the alternatives
**Nav2** (navigation), **MoveIt 2** (manipulation planning), **ros2_control** (hardware
abstraction and controller lifecycle), **tf2** (⚠️ **coordinate transforms — see §3.4**),
**rviz2**, **Foxglove** (⚠️ **the better visualization and log-inspection tool for
serious work**), **rosbag2**, **micro-ROS** (microcontrollers).

**⚠️ Not everyone uses ROS, and the reasons are legitimate.** Boston Dynamics, most
autonomous-vehicle stacks, and aerospace flight software use bespoke internal frameworks —
because they need certified real-time behaviour, tighter control over scheduling and
memory, or a safety case ROS can't currently support. **The alternatives worth knowing**:
**LCM**, **Zenoh standalone**, **eProsima/DDS directly**, **Cyphal/UAVCAN** (⚠️ **the
standard for drone and spacecraft component buses**), and **PX4/ArduPilot** for
flight control.

---
