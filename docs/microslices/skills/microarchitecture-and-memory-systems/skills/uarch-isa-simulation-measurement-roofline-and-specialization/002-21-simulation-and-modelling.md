---
id: skill-21-simulation-and-modelling-82074833cc
purpose: 21 simulation and modelling
source: src/vibey_tools/skills/plugins/microarchitecture-and-memory-systems/skills/uarch-isa-simulation-measurement-roofline-and-specialization/SKILL.md
requires: ["skill-20-isa-design-11689599ef"]
links: ["skill-22-measuring-it-407fbb402b"]
---

## §21. Simulation and Modelling

**⚠️ How architecture is evaluated before silicon exists.**
⚠️ **Cycle-accurate simulators (gem5) are accurate and extremely slow; ⚠️ trace-driven and
analytical models are fast and lossy; ⚠️ FPGA prototyping sits between.**
**⚠️ The methodology problems are severe and well documented**: ⚠️ **benchmark selection
bias, simulation of short samples that miss warm-up and phase behaviour, and validation
against real hardware that is often not done.**
**⚠️ The honest position**: ⚠️ **simulator results are hypotheses about relative ordering,
not predictions of absolute performance** (see a manufacturing reference on treating
simulation as a hypothesis generator).

---
