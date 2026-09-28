---
id: skill-8-power-fbfe972514
purpose: 8 power
source: src/vibey_tools/skills/plugins/electrical-engineering/skills/ee-semiconductors-op-amps-logic-and-power/SKILL.md
requires: ["skill-7-digital-logic-and-interfacing-655dbae1c7"]
links: []
---

## §8. Power

### 8.1 Regulator types
| Type | Efficiency | ⚠️ Notes |
|---|---|---|
| **Linear / LDO** | ⚠️ **V_out/V_in** | Simple, quiet, ⚠️ **burns the difference as heat** |
| **Buck (step-down)** | 85–95% | Switching noise; needs layout care |
| **Boost (step-up)** | 85–95% | ⚠️ **Cannot current-limit or disconnect a shorted output** |
| **Buck-boost / SEPIC** | 80–90% | In or out of range either way |
| **Charge pump** | moderate | Small currents, no inductor |
| **Isolated (flyback etc.)** | varies | Safety isolation (§14 → `ee-test-selection-safety-and-debugging`) |

**⚠️ The LDO heat calculation people skip**: dropping 12 V to 3.3 V at 500 mA dissipates
`(12−3.3)×0.5 = 4.35 W` **in a package that probably can't shed it.** ⚠️ **Efficiency is
27%.** **Use a buck.** **LDOs are for small drops, small currents, or clean analogue
rails downstream of a switcher.**

**⚠️ Dropout voltage** — an LDO needs `V_in > V_out + V_dropout`. **A "5 V to 3.3 V" LDO
with 1.2 V dropout stops regulating as the battery sags.**

### 8.2 Switching supply practicalities
**⚠️ The layout is the design.** The high-`di/dt` loop (input cap → switch → diode/synchronous
FET) must be **physically tiny**, or you radiate and get ringing. **Follow the datasheet's
reference layout — this is not the place for creativity.**
**Feedback divider** near the IC, sensed at the load if possible. **Output ripple** set by
inductor, output cap ESR, and frequency. **Inductor saturation** (§2.3 → `ee-fundamentals-components-and-circuit-analysis`) is the classic
failure.

### 8.3 Sequencing, protection, batteries
**⚠️ Power sequencing matters** — many parts require rails to come up in a specific order,
and violating it can latch up or damage them. Check the datasheet.
**Protection**: fuses (⚠️ **slow — they protect the wiring, not the semiconductors**),
PTC resettable fuses, TVS diodes, ideal-diode controllers, inrush limiting.

**Batteries**: Li-ion nominal 3.7 V (⚠️ **4.2 V full, ~3.0 V empty — a 40% swing your
design must tolerate**), LiFePO₄ 3.2 V (safer, flatter), alkaline 1.5 V (⚠️ **sloping
discharge**), NiMH 1.2 V. **⚠️ Li-ion demands protection circuitry — overcharge,
overdischarge, overcurrent, and temperature.** **Capacity in mAh is at a specified
discharge rate**; ⚠️ **actual capacity falls at high current (Peukert), and falls badly in
the cold.**

**Sleep-mode budgeting**: ⚠️ **quiescent current of the regulator often dominates a
battery device's average consumption** — an LDO drawing 50 µA quiescent defeats an MCU
sleeping at 2 µA.
