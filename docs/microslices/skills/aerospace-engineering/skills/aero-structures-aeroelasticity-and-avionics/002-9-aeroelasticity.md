---
id: skill-9-aeroelasticity-2131fc5f83
purpose: 9 aeroelasticity
source: src/vibey_tools/skills/plugins/aerospace-engineering/skills/aero-structures-aeroelasticity-and-avionics/SKILL.md
requires: ["skill-8-structures-and-materials-771f1c25fe"]
links: ["skill-10-flight-controls-and-avionics-67c05081db"]
---

## §9. Aeroelasticity

**⚠️ The interaction of aerodynamic, elastic and inertial forces — and the source of
several classes of sudden, total failure.**
```
DIVERGENCE          ⚠️ static: twist increases lift increases twist → structural failure
CONTROL REVERSAL    ⚠️ wing twist from an aileron overcomes the aileron's own effect,
                    so the control works BACKWARDS above a critical speed
FLUTTER             ⚠️ dynamic: bending and torsion modes couple and extract energy
                    from the airflow. Can destroy an aircraft in SECONDS
BUFFET, LCO, GUST RESPONSE
```
> **⚠️ GOTCHA — flutter is the aerospace failure mode that gives no warning and allows no
> reaction time.** ⚠️ **Below the flutter speed the motion damps; above it, it grows
> exponentially.** **The boundary is sharp.** **This is why flight test envelope expansion
> is incremental and instrumented, why mass balancing of control surfaces is mandatory,
> and why you never modify a control surface's mass distribution without reanalysis.**
> **⚠️ Tacoma Narrows was the civil-engineering cousin of this — aeroelastic flutter, not
> resonance** (see a Newtonian-mechanics reference §8).

---
