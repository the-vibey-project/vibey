---
id: skill-17-mission-architecture-and-the-design-cascade-c4264fc4ce
purpose: 17 mission architecture and the design cascade
source: src/vibey_tools/skills/plugins/military-space-rockets-and-fusion/skills/endeavour-mission-architecture-and-spacecraft-subsystems/SKILL.md
requires: []
links: ["skill-18-spacecraft-power-and-thermal-control-c22f9581f6"]
---

## §17 Mission architecture and the design cascade

The design cascade flows downward while mass flows upward, and the loop closes only by iteration:

    science/mission objectives → measurement requirements → instrument selection
      → pointing, power, data volume, thermal requirements → bus sizing
      → mass and volume → launch vehicle and trajectory → constrains everything above

> **THE CHARACTERISTIC MISTAKE IS TREATING THIS AS A WATERFALL.** It converges only if you carry
> margins and re-run the loop when any element grows. A cascade run once, forward, with no reserve
> produces a design that cannot absorb the first instrument that gains a kilogram.

### The architecture trades

| Trade | Poles |
|---|---|
| Flyby / orbiter / lander / rover / sample return | Cost and risk rise steeply; so does science return per target |
| Solar vs. radioisotope | Decided largely by heliocentric distance and duty cycle |
| Chemical vs. electric propulsion | Time versus propellant mass |
| Direct vs. gravity assist | Δv versus flight time and window rigidity |
| Store-and-forward vs. direct-to-Earth | Relay orbiters transform surface data return |

### Windows, porkchops and assists

**Launch windows** are set by planetary geometry. The Mars synodic period is ≈ 25.6 months — miss
the window and you wait over two years, which is the single hardest scheduling constraint in
planetary exploration; the Mars-specific consequences for crewed transfers are at §31 →
`endeavour-mars-mission-design-and-settlement`.

**Porkchop plots** — contours of C₃ (launch energy) and arrival v_∞ over departure and arrival
dates — are the working tool of mission design.

**Gravity assists** buy Δv at the cost of rigidity and flight time. Cassini's VVEJGA
(Venus-Venus-Earth-Jupiter) took ~7 years to Saturn; direct would have needed a launch vehicle that
did not exist. **Assists do not just save propellant — they enable missions outright.** The
underlying two-body relations, the Oberth effect and plane-change costs are at §11 →
`endeavour-orbits-ascent-structures-and-reentry`.
