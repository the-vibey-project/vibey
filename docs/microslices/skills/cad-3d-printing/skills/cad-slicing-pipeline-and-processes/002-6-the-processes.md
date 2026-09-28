---
id: skill-6-the-processes-2ef7dac410
purpose: 6 the processes
source: src/vibey_tools/skills/plugins/cad-3d-printing/skills/cad-slicing-pipeline-and-processes/SKILL.md
requires: ["skill-5-the-slicing-pipeline-fcbe3de4aa"]
links: []
---

## §6. The Processes

| Process | How | Resolution | ⚠️ Notes |
|---|---|---|---|
| **FDM/FFF** | Extrude molten filament | 0.1–0.3 mm layers | ⚠️ **Cheapest, most common, ANISOTROPIC (§6.1)** |
| **SLA/DLP/MSLA** | Photopolymerize resin | ⚠️ **25–100 µm** | Excellent detail; ⚠️ **brittle, UV-degrading, messy post-processing** |
| **SLS** | Laser-sinter nylon powder | ~100 µm | ⚠️ **No supports needed — the powder bed supports. Great for complex geometry** |
| **MJF** | Fusing agent + IR, powder | ~80 µm | Similar to SLS, faster, good properties |
| **Binder jetting** | Binder into powder, then sinter | — | ⚠️ **Significant sintering shrinkage to compensate** |
| **SLM/DMLS** | Laser-melt metal powder | 20–50 µm | ⚠️ **Residual stress; needs supports AND heat treatment AND removal from plate** |
| **Material jetting** | Inkjet photopolymer | ⚠️ **16 µm** | Multi-material, full colour; expensive |
| **DED** | Blown powder/wire + laser | coarse | Repair, large parts |

### 6.1 ⚠️ FDM physics — what actually determines part quality
**Layer adhesion is thermal welding of polymer chains across the interface**, and it is
**weaker than the bulk material.**
> **⚠️ GOTCHA — FDM parts are anisotropic, typically 20–50% weaker in Z (across layers)
> than in XY.** **This is the single most important design fact in FDM**: ⚠️ **part
> orientation is a structural decision, not a print-time convenience.** **Orient so that
> load paths run along layers, never across them.**

**Warping** is differential thermal contraction: the first layers cool and shrink while
upper material is still hot. ⚠️ **Worse with high-shrinkage materials (ABS, nylon), larger
footprints, and sharp corners** — hence enclosures, heated beds, and brims.
**Elephant's foot** — the first layer squashed by nozzle pressure and bed heat;
compensate in the slicer.
**Stringing** — molten material oozing on travel; retraction and temperature are the
levers.
**Bridging** — unsupported horizontal spans work because the extrudate is under tension and
cooled fast; ⚠️ **reliable to roughly 50 mm with good part cooling.**

### 6.2 SLA and powder specifics
**SLA**: ⚠️ **supports are needed even for overhangs the part could self-support, because
peel forces during separation are the dominant load.** **Hollow + drain holes** to save
resin and avoid suction cups. ⚠️ **Post-cure is required for final properties, and
over-curing makes parts brittle.**
**SLS/MJF**: ⚠️ **design for powder escape — fully enclosed voids trap unfused powder
permanently.** **Nesting in 3D is what makes it economical.**
**Metal**: ⚠️ **residual stress can distort or crack parts on the plate; supports are
structural (holding shape against stress) not just gravitational, and stress relief before
removal is standard.**
