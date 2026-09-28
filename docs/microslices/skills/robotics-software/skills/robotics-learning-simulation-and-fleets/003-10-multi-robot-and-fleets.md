---
id: skill-10-multi-robot-and-fleets-7933322c6d
purpose: 10 multi robot and fleets
source: src/vibey_tools/skills/plugins/robotics-software/skills/robotics-learning-simulation-and-fleets/SKILL.md
requires: ["skill-9-simulation-and-sim-to-real-42fee9aa6e"]
links: []
---

## §10. Multi-Robot and Fleets

**Coordination**: centralized (optimal, ⚠️ **single point of failure**) vs. decentralized
(robust, suboptimal) vs. market/auction-based task allocation. **Multi-agent path finding**
(CBS and variants) for warehouse-scale routing. **Traffic management** and deadlock
avoidance — ⚠️ **deadlock in a fleet of AMRs is a real and recurring production problem**,
not a theoretical one.

**[DURABLE] Fleet software is a distributed systems problem wearing a robotics costume** —
everything a cloud reference says about consensus, partition tolerance, idempotency and
at-least-once delivery applies, **with the added constraint that the actuators keep moving
during a partition.** ⚠️ **Design what a robot does when it loses contact with the fleet
manager, explicitly.**

**Also**: **Open-RMF** for heterogeneous fleet interop, **OTA update strategy** (⚠️ **with
staged rollout and rollback — you cannot brick a fleet**), remote operation and
teleoperation fallback, and observability across a fleet.
