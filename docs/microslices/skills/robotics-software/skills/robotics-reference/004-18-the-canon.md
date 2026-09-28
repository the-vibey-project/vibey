---
id: skill-18-the-canon-c810504b12
purpose: 18 the canon
source: src/vibey_tools/skills/plugins/robotics-software/skills/robotics-reference/SKILL.md
requires: ["skill-17-currency-snapshot-verified-august-2026-41a96e5e78"]
links: ["skill-19-quick-reference-c1c93840e1"]
---

## §18. The Canon

### 18.1 Books

| Author | Work | Why |
|---|---|---|
| **Thrun, Burgard & Fox** | ***Probabilistic Robotics*** | ⚠️ **The foundational text for §4 → `robotics-stack-ros2-and-perception`.** Still unmatched |
| **Siciliano & Khatib (eds.)** | *Springer Handbook of Robotics* | The comprehensive reference |
| **Lynch & Park** | ***Modern Robotics*** | ⚠️ **Free PDF, excellent companion course. The best modern kinematics/dynamics text** |
| **LaValle** | ***Planning Algorithms*** | Free online. §5 → `robotics-planning-control-and-manipulation`, definitively |
| **Corke** | *Robotics, Vision and Control* | Practical, MATLAB/Python, very readable |
| **Siciliano et al.** | *Robotics: Modelling, Planning and Control* | The standard graduate text |
| **Åström & Murray** | ***Feedback Systems*** | Free. ⚠️ **The best control-theory introduction for engineers** |
| **Rawlings, Mayne & Diehl** | *Model Predictive Control* | §6 → `robotics-planning-control-and-manipulation`'s MPC, rigorously |
| **Sutton & Barto** | *Reinforcement Learning* | Free. The foundation for §8 → `robotics-learning-simulation-and-fleets` |
| **Barfoot** | *State Estimation for Robotics* | Free. Modern, factor-graph-oriented |
| **Kirk** | *The Reasoned Schemer*-adjacent — no; **Nancy Leveson**, *Engineering a Safer World* | ⚠️ **The best book on system safety thinking, and it reframes §13 → `robotics-safety-standards-and-deployment`** |

### 18.2 Primary sources and tooling
**ROS 2 documentation and REPs** (⚠️ **REP-103 on units and conventions is the one to read
before your first transform bug**), **Nav2** and **MoveIt 2** docs, **OMPL**, **Drake**,
**MuJoCo**, **Isaac Lab**, **GTSAM** and **Ceres**, **PX4/ArduPilot**, **NASA cFS** and
the **JPL Power of 10 rules**, **ISO/A3** for the standards themselves (⚠️ **buy the
standard; do not work from summaries, including this one**), **Open X-Embodiment** and
**LeRobot** (HuggingFace's robotics stack).

**Conferences worth tracking**: **ICRA**, **IROS**, **RSS**, **CoRL** (⚠️ **CoRL is where
the learning-side work lands first**), **Humanoids**, **ROSCon**.

### 18.3 People and groups
**Sebastian Thrun**, **Dieter Fox**, **Pieter Abbeel**, **Sergey Levine** and **Chelsea
Finn** (⚠️ **the learning side; Physical Intelligence's π-series**), **Russ Tedrake**
(⚠️ **MIT/TRI — *Underactuated Robotics* is a superb free course, and he is unusually
candid about what learning does and doesn't solve**), **Marc Raibert** (Boston Dynamics,
now the Boston Dynamics AI Institute), **Aaron Ames** (formal safety, control barrier
functions), **Nancy Leveson** (system safety, STPA), **Steve LaValle**, **Frank Dellaert**
(factor graphs, GTSAM), **Nathan Ratliff** and **Jim Mainprice** (optimization-based
planning), **Open Robotics / OSRF** and **Tully Foote** (ROS), **Brian Gerkey**.

---
