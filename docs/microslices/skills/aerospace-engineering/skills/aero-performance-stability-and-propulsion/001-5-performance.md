---
id: skill-5-performance-c681b4c5c3
purpose: 5 performance
source: src/vibey_tools/skills/plugins/aerospace-engineering/skills/aero-performance-stability-and-propulsion/SKILL.md
requires: []
links: ["skill-6-stability-and-control-ea2fc7e91a"]
---

## §5. Performance

**Steady level flight**: `L = W`, `T = D`.
**⚠️ Breguet range equation** — the single most important performance relation:
```
Jet:      R = (V/c)·(L/D)·ln(W_i/W_f)
Propeller: R = (η/c)·(L/D)·ln(W_i/W_f)
```
⚠️ **Range depends on aerodynamic efficiency (L/D), propulsive efficiency (SFC), and the
LOGARITHM of the weight fraction.** **The log is the crucial part: doubling fuel does not
double range.** **This is the atmospheric sibling of the rocket equation, and it has the
same structure for the same reason.**

**Climb**: `rate of climb = excess power / weight`. ⚠️ **Best rate of climb (V_y) and best
angle of climb (V_x) are different speeds and answer different questions — V_x for
obstacle clearance, V_y for getting to altitude quickly.**
**Turning**: `n = 1/cos φ`; ⚠️ **a 60° bank is 2g and raises stall speed by 41%.**
**The `V-n` diagram** bounds manoeuvre and gust loads.
**Takeoff and landing distance**, **service ceiling**, ⚠️ **and the payload-range diagram,
whose kinks correspond to trading payload for fuel at MTOW.**

---
