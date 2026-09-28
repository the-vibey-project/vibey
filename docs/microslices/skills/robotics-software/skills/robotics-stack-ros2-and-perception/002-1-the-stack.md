---
id: skill-1-the-stack-1b347a9e06
purpose: 1 the stack
source: src/vibey_tools/skills/plugins/robotics-software/skills/robotics-stack-ros2-and-perception/SKILL.md
requires: ["skill-0-routing-13dabb5a44"]
links: ["skill-2-ros-2-and-middleware-22e45f3041"]
---

## §1. The Stack

**[DURABLE] Every serious robot stack has these layers, whatever the vendor calls them:**

```
   MISSION / TASK PLANNING     what should the robot accomplish?      (§1.2)
            ↓
   BEHAVIOUR / EXECUTIVE        behaviour trees, state machines       (§1.2)
            ↓
   MOTION PLANNING              collision-free trajectories           (§5)
            ↓
   CONTROL                      track the trajectory. 100Hz–10kHz     (§6)
            ↓
   HARDWARE ABSTRACTION         drivers, EtherCAT, CAN, actuators
   ─────────────────────────────────────────────────────────────
   PERCEPTION → STATE ESTIMATION feeds every layer above       (§3, §4)
   ─────────────────────────────────────────────────────────────
   SAFETY LAYER                 ⚠️ independent, often separate silicon (§13)
```

**[DURABLE] The rate hierarchy is the thing to internalize**, because it dictates
architecture: **control loops run at 100Hz–10kHz with hard deadlines; state estimation at
50–500Hz; perception at 10–60Hz; planning at 1–10Hz; mission planning whenever.**
⚠️ **The layers must be decoupled such that a slow planner cannot stall a fast controller** —
that decoupling is the single most important structural decision in the stack.

### 1.2 Behaviour orchestration
**Finite state machines** — explicit, verifiable, ⚠️ **and they explode combinatorially**
as behaviours multiply. **Behaviour trees** — ⚠️ **the modern default**, because they're
modular, reactive, and composable; `BehaviorTree.CPP` and Nav2's BT navigator are the
common implementations. **Task and motion planning (TAMP)** integrates symbolic planning
with geometric feasibility. **⚠️ LLM/VLM-driven task planning** is the newest layer (§8.2 → `robotics-learning-simulation-and-fleets`)
and the least mature.

**[DURABLE] Whatever you use, the requirement is the same: at any moment you must be able
to say what the robot is doing and why, and you must be able to stop it.**

---
