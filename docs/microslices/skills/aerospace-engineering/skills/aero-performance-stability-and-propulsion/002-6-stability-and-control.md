---
id: skill-6-stability-and-control-ea2fc7e91a
purpose: 6 stability and control
source: src/vibey_tools/skills/plugins/aerospace-engineering/skills/aero-performance-stability-and-propulsion/SKILL.md
requires: ["skill-5-performance-c681b4c5c3"]
links: ["skill-7-air-breathing-propulsion-72086cbbc8"]
---

## §6. Stability and Control

**⚠️ Static stability is the tendency to return toward equilibrium; dynamic stability is
whether the resulting oscillation damps.** **You can be statically stable and dynamically
unstable.**

**⚠️ Longitudinal stability comes down to CG position:**
- **The neutral point** is where `dC_m/dα = 0`. ⚠️ **CG ahead of it = stable; static
  margin is the distance between them as a fraction of chord.**
- **⚠️ Forward CG: more stable, heavier control forces, higher stall speed, more trim
  drag. Aft CG: lighter controls, less trim drag, and dangerous past the aft limit.**
  **This is why CG limits exist and why loading matters.**
- ⚠️ **Deliberately relaxed static stability (fighters) buys manoeuvrability and trim drag
  reduction, and it makes the aircraft unflyable without a flight control computer** (§10 → `aero-structures-aeroelasticity-and-avionics`).

**Lateral-directional**: dihedral effect (roll due to sideslip), weathercock stability.
**⚠️ The classic dynamic modes:**
```
Phugoid          ⚠️ slow, lightly damped exchange of altitude and airspeed. Easily flown
Short period     fast pitch oscillation. ⚠️ Must be well damped — it's what the pilot feels
Dutch roll       ⚠️ coupled yaw-roll oscillation; yaw dampers exist for this
Spiral mode      slow divergence into a tightening turn
Roll subsidence  heavily damped, benign
```
**Control surfaces**: elevator, aileron (⚠️ **adverse yaw — the down-going aileron adds
more drag, so you need rudder coordination or differential/Frise ailerons**), rudder,
plus spoilers, canards, elevons, ruddervators.
**⚠️ Spin** — autorotation in a stalled condition, with one wing more stalled than the
other. **Recovery is type-specific and the standard sequence (PARE) is not universal.**

---
