---
id: skill-20-compute-9980680245
purpose: 20 compute
source: src/vibey_tools/skills/plugins/medicine-design-software-development/skills/drugdev-pipeline-engineering-compute-and-regulated-software/SKILL.md
requires: ["skill-19-pipeline-engineering-06c46e5e37"]
links: ["skill-21-reproducibility-41703d4009"]
---

## §20. Compute

**⚠️ The workloads are heterogeneous and sizing them wrong is expensive:**
```
⚠️ EMBARRASSINGLY PARALLEL  docking, descriptor calculation, virtual
   screening. ⚠️ Scale horizontally; cheap; spot instances are ideal
⚠️ GPU-BOUND  MD, deep learning, ⚠️ free energy (§12)
⚠️ LONG-RUNNING  MD trajectories — ⚠️ checkpointing is mandatory
⚠️ MEMORY-BOUND  large structure and trajectory analysis
```
**⚠️ Storage is the underestimated cost**: ⚠️ **MD trajectories are enormous, and the
policy question — what to keep, at what frame rate, for how long — should be decided
before you generate terabytes.**
**⚠️ Licensing** is a real architectural constraint in this field: ⚠️ **several key
commercial tools are node- or token-licensed, which limits how you can scale.**

---
