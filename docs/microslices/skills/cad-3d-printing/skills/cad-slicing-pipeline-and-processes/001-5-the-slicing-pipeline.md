---
id: skill-5-the-slicing-pipeline-fcbe3de4aa
purpose: 5 the slicing pipeline
source: src/vibey_tools/skills/plugins/cad-3d-printing/skills/cad-slicing-pipeline-and-processes/SKILL.md
requires: []
links: ["skill-6-the-processes-2ef7dac410"]
---

## §5. The Slicing Pipeline

**⚠️ Slicing is where a geometric model becomes a manufacturing plan, and most of the
part's real properties are decided here.**

```
MESH → orient & place → repair/validate
  → SLICE into layers (plane-mesh intersection → closed 2D polygons)
    → PERIMETERS (offset inward by nozzle width, n times)
      → SOLID top/bottom regions & INFILL of the remainder
        → SUPPORT generation for overhangs
          → path planning & ordering → travel moves & retractions
            → EXTRUSION calculation (E per mm) → G-CODE
```

### 5.1 The slicing step itself
**Intersect the mesh with a horizontal plane per layer.** ⚠️ **The output must be closed
polygons; a non-manifold or leaking mesh produces open contours, and the slicer must
guess — which is exactly the "slicer repaired 588 errors" message.**
**Robustness tricks**: perturb the plane slightly to avoid exact vertex/edge coincidence,
and **use exact predicates or careful epsilon handling** — ⚠️ **the same numerical problem
as §2 → `cad-geometry-kernels-formats-and-code-cad`.**

### 5.2 The 2D operations that follow
**Polygon offsetting (Minkowski/Clipper)** for perimeters — ⚠️ **offsetting is
non-trivial: thin regions collapse, and self-intersections must be resolved.**
**Boolean operations** for infill clipping. **Even-odd or nonzero winding** for holes.
**⚠️ The Clipper library does most of this heavy lifting across the open slicers.**

### 5.3 The decisions that matter
**Infill patterns**: grid, gyroid (⚠️ **isotropic and non-crossing — good strength per
material, and popular for flexibles**), honeycomb, lightning (⚠️ **minimal, only supports
top surfaces**), cubic. **Infill density is sharply non-linear in benefit** — ⚠️ **beyond
about 40–50%, adding infill buys much less strength than adding perimeters.**

**Supports**: normal vs **tree/organic** (⚠️ **less material, easier removal, better
surface — the default choice now where supported**). **Overhang threshold** typically
45–55°. **Interface layers** determine the surface you get after removal.

**⚠️ Adhesion and warping**: brim, raft, skirt; and the physics is thermal contraction
(§6.1).

### 5.4 G-code
```
G0/G1 X Y Z E F     ⚠️ coordinated move; E is EXTRUDER AXIS POSITION, not a rate
G28                 home
G29                 bed level / mesh probe
M104/M109           set / set-and-wait hotend temp
M140/M190           set / set-and-wait bed temp
M106/M107           fan on / off
G90/G91             absolute / relative positioning
M82/M83             ⚠️ absolute / relative EXTRUSION — a separate mode from G90/G91
G92                 set position without moving  ⚠️ (E0 resets extruder origin)
```
**⚠️ Extrusion is computed, not commanded by volume**:
```
E_mm = (layer_height × extrusion_width × distance) / (π × (filament_d/2)²)
```
**Multiply by extrusion multiplier / flow.** ⚠️ **This is why filament diameter accuracy
matters — a nominal 1.75 mm filament that's actually 1.70 mm under-extrudes by ~6%.**

**⚠️ Firmware differences are real**: Marlin, Klipper (⚠️ **input shaping and pressure
advance move motion planning to a Linux host — and it changes what the slicer should
emit**), RepRapFirmware, Prusa's fork. **Flavour selection in the slicer is not cosmetic.**

**Post-processing scripts** are the underused power feature: ⚠️ **every major slicer can
run a script over the G-code before saving.** Use it for custom pauses (filament change
at layer N), Z-hop tweaks, adding M73 progress, or injecting per-object settings. **It's
just text processing.**

---
