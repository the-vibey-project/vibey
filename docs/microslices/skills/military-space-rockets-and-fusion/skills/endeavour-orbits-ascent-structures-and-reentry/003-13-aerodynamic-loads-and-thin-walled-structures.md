---
id: skill-13-aerodynamic-loads-and-thin-walled-structures-06799f35c8
purpose: 13 aerodynamic loads and thin walled structures
source: src/vibey_tools/skills/plugins/military-space-rockets-and-fusion/skills/endeavour-orbits-ascent-structures-and-reentry/SKILL.md
requires: ["skill-12-the-ascent-trajectory-and-the-v-budget-eadd2b2c32"]
links: ["skill-14-guidance-and-control-c3e724f2f2"]
---

## §13 Aerodynamic loads and thin-walled structures

**Dynamic pressure q = ½ρv² drives everything structural in the atmosphere**, and the metric vehicles
are actually flown to is the **q·α product**: guidance limits q·α, and **wind shear is dangerous
precisely because it creates α the vehicle did not command**.

Launch vehicles are **aerodynamically unstable** — centre of pressure ahead of centre of mass — and are
**actively stabilized by thrust vectoring**, so **a control failure is immediately catastrophic** (§14 below).

**Acoustic loads at liftoff are 160–180 dB OASPL.** Water deluge is **not primarily cooling — it is acoustic
suppression**, protecting the payload and vehicle from reflected acoustic energy that could shake components
apart.

### Buckling governs, not yielding

| Structural fact | Consequence |
|---|---|
| Thin-walled cylinder axial buckling uses a **knockdown factor γ of 0.15–0.65** | real cylinders are **exquisitely sensitive to imperfections**; **classical theory over-predicts buckling strength by up to 5×** |
| **Pressure stabilization** — internal pressure adds tensile stress that raises the effective buckling threshold | Atlas's **balloon tanks** took this to the limit: the vehicle **would collapse under its own weight if depressurized** |
| **Hoop stress is twice longitudinal stress** — σ_h = pR/t, σ_l = pR/(2t) | cylindrical tanks **fail along a longitudinal seam**, so **weld orientation matters** |

**POGO** is a closed-loop instability: structural longitudinal modes → feedline pressure oscillation → thrust
oscillation → back into the structure. It **nearly destroyed Apollo 13's S-II**, and is suppressed with
**gas-filled accumulators in the feedlines that detune the hydraulic resonance**.
