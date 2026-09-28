---
id: skill-11-molecular-dynamics-705ed12bb0
purpose: 11 molecular dynamics
source: src/vibey_tools/skills/plugins/medicine-design-software-development/skills/drugdev-protein-structure-docking-and-molecular-dynamics/SKILL.md
requires: ["skill-10-docking-e5b9961981"]
links: ["skill-12-free-energy-methods-ed4e55e806"]
---

## §11. Molecular Dynamics

**⚠️ Simulating atomic motion under a force field — the tool for questions docking can't
answer.**
**Force fields** (**AMBER, CHARMM, OPLS, and ⚠️ increasingly ML potentials**), **and
⚠️ the ligand parameterization problem: proteins are well-parameterized, arbitrary small
molecules are not, and bad ligand parameters invalidate the whole simulation.**
**⚠️ Engines**: **GROMACS, AMBER, OpenMM (⚠️ the most programmable), NAMD, Desmond.**
**⚠️ The timescale problem is the honest limitation**: ⚠️ **routine simulations reach
microseconds; many biologically relevant motions take milliseconds to seconds.**
**⚠️ Enhanced sampling (metadynamics, replica exchange, umbrella sampling) exists to
attack exactly this gap.**
**⚠️ What MD is genuinely good for**: **binding site flexibility and cryptic pockets,
water networks, stability of a docked pose, and generating ensembles for §10.**

---
