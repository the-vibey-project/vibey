---
id: skill-12-testing-debugging-and-deployment-070457cd15
purpose: 12 testing debugging and deployment
source: src/vibey_tools/skills/plugins/robotics-software/skills/robotics-safety-standards-and-deployment/SKILL.md
requires: ["skill-11-real-time-and-safety-critical-engineering-7fd6545d56"]
links: ["skill-13-functional-safety-and-standards-ca9acfbfe8"]
---

## §12. Testing, Debugging, and Deployment

**[DURABLE] The testing pyramid, robotics edition:**
```
Unit                     pure logic, no hardware. Fast, and undervalued
Component-in-sim         one node against simulated inputs
Integration-in-sim       full stack, scripted scenarios, in CI
Hardware-in-the-loop     real compute + real timing, simulated world  ⚠️ high value
Real hardware, safe env  cage, tether, E-stop, reduced speed/power
Field trials             real environment, safety operator
Production               with monitoring, and a rollback path
```

**⚠️ HIL is the most under-invested rung** and catches the timing and driver bugs that
pure simulation cannot.

**[DURABLE] Debugging discipline specific to robots:**
- **⚠️ Record everything, always.** `rosbag`/MCAP of every run, including failures.
  **A robot failure you didn't record is a failure you cannot fix**, because you may not
  reproduce it.
- **Deterministic replay** from logs — the single most valuable debugging capability in
  the field.
- **Visualize** — rviz2 and Foxglove. ⚠️ **Most perception and transform bugs are obvious
  the moment you look at them and invisible in numbers** (§3.4 → `robotics-stack-ros2-and-perception`).
- **Check the transform tree and timestamps first.** §3.4 → `robotics-stack-ros2-and-perception` is genuinely the first
  hypothesis, not the last.
- **Bisect the stack**: replay recorded sensor data into a live planner; feed synthetic
  perfect perception into control. **Isolate which layer is lying.**
- **⚠️ Watch for correlated failures.** Robots fail in cascades — a perception dropout
  causes a planner stall causes a controller timeout causes an E-stop.

**Field deployment**: staged rollout, ⚠️ **shadow mode** (run the new policy without
letting it actuate, and compare), extensive telemetry, remote diagnostics,
**a rollback path that works without physical access**, and **an incident process
that treats near-misses as reportable.**

---
