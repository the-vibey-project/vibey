---
id: skill-8-tolerances-and-fits-4f36ab2e4d
purpose: 8 tolerances and fits
source: src/vibey_tools/skills/plugins/cad-3d-printing/skills/cad-design-tolerances-and-materials/SKILL.md
requires: ["skill-7-design-for-additive-manufacturing-2a4a5d36f5"]
links: ["skill-9-materials-0fe7c7259c"]
---

## §8. Tolerances and Fits

**⚠️ The dimensions you model are not the dimensions you get.** Sources: extrusion width
and flow, thermal shrinkage, elephant's foot, backlash, and slicer offset behaviour.

```
⚠️ FDM typical accuracy    ±0.1–0.5 mm (dimension-dependent)
SLA                         ±0.05–0.15 mm
SLS/MJF                     ±0.15–0.3 mm
Metal (post-processed)      ±0.1 mm, better with machining
```
**⚠️ Holes print undersize on FDM** — the extrudate on the inside of a curve compresses
inward. **Oversize modelled holes by 0.1–0.4 mm, or design for a drill/tap operation.**

**Practical clearances (FDM, per side)**:
```
Press fit          0.0 to −0.1 mm    ⚠️ interference
Tight sliding      0.15–0.2 mm
Free running       0.3–0.4 mm
Print-in-place     0.3–0.5 mm        ⚠️ (§7)
```
**⚠️ Calibrate your own machine and material rather than trusting these** — a tolerance
test print with a range of clearances takes 20 minutes and is worth more than any table.

**Threads**: printed threads work above roughly M6 but are weak. ⚠️ **Heat-set inserts are
the right answer for anything load-bearing in FDM**, followed by tapping into a printed
boss, then captive nuts.

---
