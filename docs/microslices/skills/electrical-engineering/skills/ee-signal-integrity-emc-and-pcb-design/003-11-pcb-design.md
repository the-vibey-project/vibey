---
id: skill-11-pcb-design-7c047d7c19
purpose: 11 pcb design
source: src/vibey_tools/skills/plugins/electrical-engineering/skills/ee-signal-integrity-emc-and-pcb-design/SKILL.md
requires: ["skill-10-emc-and-emi-78a5c114b2"]
links: []
---

## §11. PCB Design

**Stackup**: ⚠️ **2-layer is fine for slow, low-power designs and inadequate for anything
fast.** **4-layer (signal / ground / power / signal) is the practical default** — the
ground plane pays for itself. **Keep signal layers adjacent to a reference plane.**

**Layout order that works**: connectors and mechanical constraints → power entry and
regulation → high-speed and sensitive analogue → everything else.
**⚠️ Place before you route, and place by signal flow.** Most routing pain is a placement
problem.

**Rules worth internalizing**:
- ⚠️ **Decoupling caps as close as physically possible to the pin** (§9.3).
- ⚠️ **Never cross a plane split with a fast signal** (§9.1).
- **Keep the switching regulator's high-`di/dt` loop tiny** (§8.2 → `ee-semiconductors-op-amps-logic-and-power`).
- **Match lengths for parallel buses and differential pairs; route pairs together.**
- **Thermal relief on pads connected to planes** — ⚠️ **or you cannot hand-solder them.**
- **Copper pour and thermal vias for heat.**
- ⚠️ **Test points on every rail, key signals, and ground — cheap now, priceless at
  debug time** (§15 → `ee-test-selection-safety-and-debugging`).
- **Silkscreen: polarity marks, pin 1, connector labels, and a version string.**

**⚠️ DFM realities**: respect the fab's minimum trace/space and drill sizes, check
annular ring, avoid acid traps, and **run DRC and actually read the output.**
**Always order a bare-board and check fit before populating a batch.**

**Tools**: **KiCad** (⚠️ **free, and now genuinely professional-grade — the right default
for most people**), Altium, Eagle/Fusion, OrCAD. **Simulation**: LTspice/ngspice
(⚠️ **free, and worth learning for power and analogue**), QUCS, and the vendor design
tools for switching regulators (⚠️ **TI WEBENCH and similar produce a working design and
a bill of materials in minutes — use them**).
