---
id: skill-11-the-combined-cycle-the-most-efficient-heat-engine-6eae416797
purpose: 11 the combined cycle the most efficient heat engine
source: src/vibey_tools/skills/plugins/engines-generators-and-fuels/skills/engines-otto-diesel-brayton-stirling-and-combined-cycles/SKILL.md
requires: ["skill-10-the-stirling-engine-a56dc9dc14"]
links: []
---

## §11 The combined cycle — the most efficient heat engine

**A Brayton (gas turbine) cycle on top, a Rankine (steam) cycle on the bottom.** Gas turbine exhaust
(**typically 500–650°C**) is not wasted: it passes through a **heat recovery steam generator (HRSG)**
making steam for a bottoming Rankine cycle. **55–62% efficiency, the highest of any heat engine in
commercial service.**

**Why it works.** The Brayton cycle's heat rejection becomes the Rankine cycle's heat source, so the
overall cycle rejects heat at a much lower average temperature than Brayton alone. In Carnot terms it
gets both ends of the lever at once:

| | T_H | T_C |
|---|---|---|
| Brayton alone | Gas turbine firing temperature **~1400–1600°C** | Exhaust to atmosphere |
| Rankine alone | Boiler / superheater temperature | Steam condenser **~30°C** |
| **Combined** | **~1400–1600°C firing temperature** | **~30°C steam condenser** |

A higher T_H **and** a lower T_C than either cycle alone. **The ultimate expression of the universal
principle** stated at the top of this skill.

Next: §12–§14 → `engines-generators-and-house-power` (turning that shaft into electricity),
§15–§17 → `engines-fuels-and-combustion` (what to burn in each), and
§21 → `engines-safety-and-reference` (the hazards around any running engine, carbon monoxide above
all).
