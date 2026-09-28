---
id: skill-5-motion-planning-9a936cfa40
purpose: 5 motion planning
source: src/vibey_tools/skills/plugins/robotics-software/skills/robotics-planning-control-and-manipulation/SKILL.md
requires: []
links: ["skill-6-control-c97f2c17a7"]
---

## §5. Motion Planning

**[DURABLE] The configuration-space framing**: planning happens in the space of robot
configurations, not in the workspace, and obstacles map into C-space as forbidden regions.
**Dimensionality is the enemy** — a 7-DOF arm plans in 7 dimensions.

| Family | Notes |
|---|---|
| **Grid/graph search** — A\*, D\* Lite, hybrid A\* | ⚠️ **Optimal and complete in the discretization**; the standard for ground vehicles. Hybrid A\* handles nonholonomic constraints |
| **Sampling-based** — RRT, RRT\*, PRM, BIT\*, informed RRT\* | ⚠️ **Probabilistically complete, scales to high DOF, non-deterministic.** The default for arms (OMPL) |
| **Optimization-based** — CHOMP, STOMP, TrajOpt | Smooth trajectories, ⚠️ **local minima** |
| **Reactive** — DWA, TEB, potential fields, VO/ORCA | Fast local avoidance. ⚠️ **Potential fields have local minima and everyone rediscovers this** |
| **Learned** | §8 → `robotics-learning-simulation-and-fleets` |

**[DURABLE] The distinction that structures every navigation stack**: a **global planner**
(slow, complete, over a known map) and a **local planner/controller** (fast, reactive,
over live sensor data). **Nav2's architecture is this made explicit.**

**⚠️ The constraints that make real planning hard**: **kinodynamic limits** (a car can't
move sideways; an arm has torque limits), **differential constraints**, **time-varying
obstacles**, ⚠️ **planning under uncertainty** — the plan must be robust to the fact that
§4 → `robotics-stack-ros2-and-perception`'s estimate is wrong — and **replanning latency**, because a plan computed for where you
were is worthless.

---
