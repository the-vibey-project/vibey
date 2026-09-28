---
id: skill-14-numbers-fb12d9e49e
purpose: 14 numbers
source: src/vibey_tools/skills/plugins/cad-3d-printing/skills/cad-reference/SKILL.md
requires: ["skill-13-anti-patterns-21e072011a"]
links: ["skill-15-books-and-tools-45008b5f12"]
---

## §14. Numbers

```
FDM
Nozzle 0.4 mm typical (0.2–0.8) · Layer 0.1–0.3 mm (⚠️ ~25–75% of nozzle Ø)
Extrusion width ≈ nozzle Ø to 1.2× · Filament 1.75 mm (or 2.85)
⚠️ Overhang limit ~45–55° · Bridging to ~50 mm with good cooling
⚠️ Z-strength 50–80% of XY · Accuracy ±0.1–0.5 mm
First layer squish, elephant's foot compensation ~0.1–0.5 mm

CLEARANCES (FDM, per side)
Press fit 0 to −0.1 · Tight sliding 0.15–0.2 · Free 0.3–0.4 · Print-in-place 0.3–0.5
⚠️ Holes print undersize: oversize by 0.1–0.4 mm

RESOLUTION BY PROCESS
Material jetting 16 µm · SLA/MSLA 25–100 µm · SLM 20–50 µm
MJF ~80 µm · SLS ~100 µm · FDM 100–300 µm

TEMPERATURES (nozzle / bed)
PLA 200/60 · PETG 240/80 · ABS 250/100 · Nylon 260/90 · PC 280/110 · TPU 225/50
⚠️ PLA softens ~60 °C — glass transition, not melting

EXTRUSION MATH
E = (layer_h × width × dist) / (π (filament_d/2)²)
⚠️ 1.75 mm nominal at 1.70 mm actual = ~6% under-extrusion

MESH
⚠️ Euler: V − E + F = 2 − 2g  for a closed surface of genus g
Manifold: every edge in exactly 2 faces
```

---
