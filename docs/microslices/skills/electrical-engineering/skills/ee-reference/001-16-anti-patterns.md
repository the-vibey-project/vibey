---
id: skill-16-anti-patterns-b8125847db
purpose: 16 anti patterns
source: src/vibey_tools/skills/plugins/electrical-engineering/skills/ee-reference/SKILL.md
requires: []
links: ["skill-17-numbers-7486a122f7"]
---

## §16. Anti-Patterns

| Anti-pattern | Why |
|---|---|
| Voltage divider as a power supply | ⚠️ **Sags under load. Use a regulator or buffer** (§1 → `ee-fundamentals-components-and-circuit-analysis`) |
| Inductive load with no flyback diode | ⚠️ **Destroys the switch, sometimes slowly** (§1 → `ee-fundamentals-components-and-circuit-analysis`) |
| Ignoring ceramic DC bias derating | ⚠️ **10 µF can be 2 µF in circuit** (§2.2 → `ee-fundamentals-components-and-circuit-analysis`) |
| Standard MOSFET driven from a 3.3 V GPIO | ⚠️ **Barely on, dissipates heat, fails** (§5.3 → `ee-semiconductors-op-amps-logic-and-power`) |
| No gate pull-down on a load switch | Load turns on during MCU reset (§5.3 → `ee-semiconductors-op-amps-logic-and-power`) |
| GPIO driving a big power FET directly | Slow edges, linear-region heat (§5.3 → `ee-semiconductors-op-amps-logic-and-power`) |
| Trusting "3.3 V and 5 V are compatible" | ⚠️ **Compare V_OH against V_IH from both datasheets** (§7.1 → `ee-semiconductors-op-amps-logic-and-power`) |
| 5 V into a non-5V-tolerant pin | ⚠️ **ESD diode conducts; slow mysterious death** (§7.2 → `ee-semiconductors-op-amps-logic-and-power`) |
| Floating CMOS input | Oscillation and heating (§7.4 → `ee-semiconductors-op-amps-logic-and-power`) |
| LDO for a large voltage drop | ⚠️ **12→3.3 V at 500 mA is 4.35 W and 27% efficient** (§8.1 → `ee-semiconductors-op-amps-logic-and-power`) |
| Ignoring LDO dropout as a battery sags | Regulation stops (§8.1 → `ee-semiconductors-op-amps-logic-and-power`) |
| Creative switching-regulator layout | ⚠️ **Follow the reference layout** (§8.2 → `ee-semiconductors-op-amps-logic-and-power`) |
| Routing a fast signal across a plane split | ⚠️ **The return current detours; that loop is an antenna** (§9.1 → `ee-signal-integrity-emc-and-pcb-design`) |
| Decoupling cap "somewhere near" the chip | Loop area is what matters (§9.3 → `ee-signal-integrity-emc-and-pcb-design`) |
| Analogue/digital ground split, routed across | Usually worse than a solid plane (§9.4 → `ee-signal-integrity-emc-and-pcb-design`) |
| Ferrite bead + bulk cap without damping | ⚠️ **LC tank that amplifies at resonance** (§2.3 → `ee-fundamentals-components-and-circuit-analysis`) |
| Uncompensated scope probe | ⚠️ **Distorted edges you'll chase for an hour** (§12.2 → `ee-test-selection-safety-and-debugging`) |
| Long crocodile ground lead on fast edges | ⚠️ **Ringing that isn't in your circuit** (§12.2 → `ee-test-selection-safety-and-debugging`) |
| Scope ground clipped to a live mains node | ⚠️ **Short through earth. Use a differential probe** (§12.2 → `ee-test-selection-safety-and-debugging`, §14 → `ee-test-selection-safety-and-debugging`) |
| Ammeter across a voltage source | Short circuit; blown fuse (§12.1 → `ee-test-selection-safety-and-debugging`) |
| First power-up without current limiting | Turns a short into scrap (§12.3 → `ee-test-selection-safety-and-debugging`, §15 → `ee-test-selection-safety-and-debugging`) |
| Designing to "typical" datasheet values | ⚠️ **Design to min/max** (§13 → `ee-test-selection-safety-and-debugging`) |
| Treating absolute maximum as an operating point | ⚠️ **Those are destruction limits** (§13 → `ee-test-selection-safety-and-debugging`) |
| Ignoring part lifecycle and stock | A design you can't build (§13 → `ee-test-selection-safety-and-debugging`) |
| Assuming low voltage means safe | ⚠️ **~100 mA is the lethal mechanism** (§14 → `ee-test-selection-safety-and-debugging`) |
| Probing a board with no test points | You'll wish you'd spent the 20 minutes (§11 → `ee-signal-integrity-emc-and-pcb-design`) |
| Changing three things then retesting | You've learned nothing (§15 → `ee-test-selection-safety-and-debugging`) |

---
