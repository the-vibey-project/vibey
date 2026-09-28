---
id: skill-1-fundamentals-01b33fcac1
purpose: 1 fundamentals
source: src/vibey_tools/skills/plugins/electrical-engineering/skills/ee-fundamentals-components-and-circuit-analysis/SKILL.md
requires: ["skill-0-routing-fab00ef62d"]
links: ["skill-2-real-components-313b1689b7"]
---

## §1. Fundamentals

```
V = I·R                    Ohm's law
P = V·I = I²R = V²/R       power  ⚠️ the I²R form is why current, not voltage, melts things
Q = C·V                    charge on a capacitor
I = C·dV/dt                ⚠️ capacitor current is proportional to RATE of voltage change
V = L·di/dt                ⚠️ inductor voltage is proportional to RATE of current change
E = ½CV²  ·  E = ½LI²      stored energy
```

**Kirchhoff**: **KCL** — current into a node equals current out (charge conservation).
**KVL** — voltages around a loop sum to zero (energy conservation). ⚠️ **Everything in
circuit analysis is these two plus component laws.**

> **⚠️ GOTCHA — the two `dV/dt` and `di/dt` relations explain most surprises.**
> - **A capacitor resists voltage change**, and **an inductor resists current change.**
> - ⚠️ **Interrupting current through an inductor generates a large voltage spike**
>   (`V = L·di/dt`, and switching gives you a huge `di/dt`). **This is why every relay and
>   motor needs a flyback diode**, and why omitting one destroys the driving transistor
>   — often not immediately, which makes it worse to diagnose.
> - ⚠️ **A discharged capacitor looks like a short circuit at the instant you connect
>   power.** This is inrush current, and it's why large supplies need soft-start.

**Series and parallel**:
```
R series: R₁+R₂     R parallel: (R₁R₂)/(R₁+R₂)
C series: like R parallel  ⚠️ (capacitors combine backwards from resistors)
C parallel: C₁+C₂
L combines like R
```

**Voltage divider** — `V_out = V_in · R₂/(R₁+R₂)`.
⚠️ **Only valid unloaded.** The moment you draw current, the ratio shifts. **Rule of
thumb: the divider's current should be at least 10× the load current**, or use a buffer
(§6 → `ee-semiconductors-op-amps-logic-and-power`). ⚠️ **A divider is not a power supply** — this is a genuinely common beginner error
that produces a rail that sags under load.

---
