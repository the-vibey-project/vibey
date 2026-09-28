---
id: skill-3-dc-analysis-580757f7af
purpose: 3 dc analysis
source: src/vibey_tools/skills/plugins/electrical-engineering/skills/ee-fundamentals-components-and-circuit-analysis/SKILL.md
requires: ["skill-2-real-components-313b1689b7"]
links: ["skill-4-ac-impedance-filters-09792fcdac"]
---

## §3. DC Analysis

**Thévenin**: any linear network = one voltage source + one series resistance.
**Norton**: current source + parallel resistance. ⚠️ **Thévenin is how you reason about
what a circuit looks like to the next stage**, and it's the formal justification for the
divider-loading rule in §1.

**Maximum power transfer** at `R_load = R_source` — ⚠️ **but that's 50% efficient, so it's
what you want for signals and RF, and emphatically not what you want for power delivery.**

**Node-voltage and mesh-current analysis** are the systematic methods; **superposition**
for multiple sources in linear circuits.

**⚠️ The practical DC skills that matter most**: calculate the current before connecting
anything, compute dissipation (`I²R`) and check it against the part's rating, and
**sanity-check that your ground return can carry what you're pushing.**

---
