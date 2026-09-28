---
id: skill-7-mechanisms-and-kinematics-f0bafc02d5
purpose: 7 mechanisms and kinematics
source: src/vibey_tools/skills/plugins/manufacturing-mechanical-engineering-for-software-devs/skills/mfg-machine-elements-mechanisms-and-tolerances/SKILL.md
requires: ["skill-6-machine-elements-a3309a4363"]
links: ["skill-8-tolerances-and-gd-t-8f6da48d18"]
---

## §7. Mechanisms and Kinematics

**⚠️ Degrees of freedom, linkages (⚠️ four-bar being the workhorse), cams, and the
distinction between kinematics (motion) and dynamics (forces causing it).**
> **⚠️ GOTCHA — EXACT CONSTRAINT (kinematic) design is the concept software people find
> most surprising and most useful.** ⚠️ **A rigid body has six degrees of freedom; constrain
> each exactly once and the assembly is deterministic.** **⚠️ OVER-CONSTRAINT — the
> intuitive "add more bolts and pins to make it solid" — forces parts to fight each other,
> transmits manufacturing variation into stress, and produces assemblies that bind or warp
> unpredictably.**
> **⚠️ The classic example: a three-legged stool never rocks; a four-legged one does,
> because it's over-constrained.**
> **⚠️ The software analogue is real: redundant sources of truth don't add robustness, they
> add contradiction.**

**⚠️ Vibration and resonance**: ⚠️ **every structure has natural frequencies; excite one and
amplitude grows until damping or failure limits it.** **⚠️ Modal analysis, damping, tuned
mass dampers, and the practical rule to keep excitation frequencies away from natural
ones.**

---
