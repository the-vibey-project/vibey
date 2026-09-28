---
id: skill-2-loads-and-structure-67d50f0643
purpose: 2 loads and structure
source: src/vibey_tools/skills/plugins/civil-industrial-engineering-for-software-devs/skills/civil-loads-safety-factors-materials-and-foundations/SKILL.md
requires: ["skill-1-why-this-comparison-keeps-coming-up-be5e9d2c72"]
links: ["skill-3-factor-of-safety-40821c80fa"]
---

## §2. Loads and Structure

```
DEAD LOAD      permanent — the structure's own weight
LIVE LOAD      ⚠️ variable and occupancy-dependent — people, furniture, traffic
ENVIRONMENTAL  wind, snow, seismic, thermal, hydrostatic
⚠️ DYNAMIC vs STATIC  ⚠️ a moving or oscillating load is not the same as its
   static equivalent — resonance and fatigue are separate failure paths
```
**⚠️ Load paths**: ⚠️ **every load must have a continuous path to the foundation, and
tracing that path is the core structural skill.** **A load path that's interrupted — by a
removed wall, a modified connection — is how buildings fail.**
**Structural elements**: **beams (bending), columns (⚠️ compression, and buckling as a
STABILITY failure distinct from crushing), ties (tension), trusses (⚠️ axial only, which
is why they're efficient), arches and cables (⚠️ shape-dependent force paths), shear walls
and bracing (lateral).**
**⚠️ The software-relevant abstraction**: ⚠️ **structural analysis is about tracing how
demand propagates to where it's ultimately resisted** — **which is exactly what
dependency and load analysis is in a distributed system, and the "interrupted load path"
failure has an exact analogue in a removed layer of redundancy nobody re-derived.**

---
