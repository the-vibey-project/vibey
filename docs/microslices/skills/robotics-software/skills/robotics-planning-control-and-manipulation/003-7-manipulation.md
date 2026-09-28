---
id: skill-7-manipulation-59df12bd8e
purpose: 7 manipulation
source: src/vibey_tools/skills/plugins/robotics-software/skills/robotics-planning-control-and-manipulation/SKILL.md
requires: ["skill-6-control-c97f2c17a7"]
links: []
---

## §7. Manipulation

**[DURABLE] Manipulation is harder than navigation, and the reason is contact.** Free-space
motion is smooth and modellable; **contact is discontinuous, high-bandwidth, and where the
models stop working.**

**Kinematics**: forward (joint angles → pose, easy), **inverse** (pose → joint angles;
⚠️ **multiple solutions, singularities, and no closed form for many arms** — IKFast,
TRAC-IK, or numerical), **Jacobians** (velocity mapping; ⚠️ **singularities are where it
loses rank and joint velocities blow up**), and **redundancy resolution** for 7-DOF arms.

**Grasping**: analytic (force closure, wrench space) vs. **learned** (⚠️ **now dominant
for unstructured objects** — GraspNet, Contact-GraspNet, Dex-Net), and the hard cases are
**deformables, transparent and reflective objects** (⚠️ **which defeat depth sensors
outright**), and **cluttered bins**.

**⚠️ The practical reality: the last centimetre is the hard part.** Getting near the object
is solved; the final approach, contact, and force regulation is where systems fail —
which is exactly why §8 → `robotics-learning-simulation-and-fleets`'s learned policies got traction here first.
