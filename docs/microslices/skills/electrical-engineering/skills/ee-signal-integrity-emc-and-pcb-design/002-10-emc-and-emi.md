---
id: skill-10-emc-and-emi-78a5c114b2
purpose: 10 emc and emi
source: src/vibey_tools/skills/plugins/electrical-engineering/skills/ee-signal-integrity-emc-and-pcb-design/SKILL.md
requires: ["skill-9-signal-integrity-and-grounding-466f144f2e"]
links: ["skill-11-pcb-design-7c047d7c19"]
---

## §10. EMC and EMI

**⚠️ Emissions are set by rise time, loop area, and common-mode current — not by clock
frequency.** `f_knee ≈ 0.35/t_rise` (§4 → `ee-fundamentals-components-and-circuit-analysis`).

**Reduce emissions by**: **minimizing loop area** (§9.1 — ⚠️ **the highest-leverage
change**), **slowing edges where you can afford to** (many MCUs have configurable slew
rate — use it), **series termination**, **shielding**, **common-mode chokes on cables**,
and **filtering at the connector, not somewhere in the middle.**

**⚠️ Cables are the antennas.** A board that passes on its own will fail with cables
attached, because **common-mode current on a cable radiates efficiently.** **Filter and
ground at the point of entry.**

**Immunity and ESD**: ⚠️ **a human-body ESD event is kilovolts with nanosecond rise times**
and will find any unprotected exposed pin. **TVS diodes at connectors**, ground the
chassis properly, and **keep the ESD current path away from sensitive circuitry** — a TVS
that dumps into a trace running past your ADC has just moved the problem.

**⚠️ Practical advice**: pre-compliance testing with a cheap near-field probe and a
spectrum analyzer catches most problems before a formal test costs you a redesign cycle.
**Design for EMC from the start; it cannot be retrofitted cheaply.**

---
