---
id: skill-11-automation-pipelines-465dce7a9b
purpose: 11 automation pipelines
source: src/vibey_tools/skills/plugins/cad-3d-printing/skills/cad-generative-automation-and-scanning/SKILL.md
requires: ["skill-10-generative-design-and-lattices-e6c3d068a1"]
links: ["skill-12-scanning-and-reverse-engineering-f28d9d6700"]
---

## §11. Automation Pipelines

**⚠️ This is where a software background pays off most.**
```
Parametric source (git) → CI build (headless CAD) → export STEP/3MF
  → automated slicing (CLI) → G-code artifact → print farm queue → telemetry
```
**Headless invocation**:
```
openscad -o part.stl -D 'width=30' -D 'height=10' part.scad
openscad -o part.3mf --backend=manifold part.scad
prusa-slicer --export-gcode --load config.ini -o out.gcode part.stl
CuraEngine slice -j printer.def.json -l model.stl -o out.gcode
python -c "import cadquery as cq; ..."      # library, no GUI needed
```
**⚠️ All the major slicers have a CLI, and this is under-exploited** — batch slicing,
regression-testing a design change against print time and material use, and generating
variant families are all straightforward once you're in a script.

**Print farm management**: **OctoPrint**, **Klipper + Moonraker + Mainsail/Fluidd**
(⚠️ **Moonraker's API is the practical integration point**), **PrintNanny**, commercial
MES. **Telemetry, queueing, and failure detection** are the operational layer.

**⚠️ Testing a CAD pipeline** is a genuinely interesting problem: assert on **bounding
box, volume, mass properties, and manifoldness**; render images and diff them; **and check
sliced output for support volume and print time** as a regression signal.

---
