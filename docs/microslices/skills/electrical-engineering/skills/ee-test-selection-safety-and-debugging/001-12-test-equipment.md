---
id: skill-12-test-equipment-984b6f376a
purpose: 12 test equipment
source: src/vibey_tools/skills/plugins/electrical-engineering/skills/ee-test-selection-safety-and-debugging/SKILL.md
requires: []
links: ["skill-13-datasheets-and-selection-1877b5a1af"]
---

## §12. Test Equipment

### 12.1 Multimeter
**⚠️ Measure voltage in parallel, current in series.** Putting an ammeter across a
voltage source is a short circuit — **that's what the fuse in your meter is for, and it's
the most common way meters die.**
**⚠️ Input impedance ~10 MΩ loads high-impedance nodes** and shifts what you're measuring.
**True-RMS matters** for anything non-sinusoidal. **Continuity, diode test, and capacitance
modes** are the daily drivers.

### 12.2 Oscilloscope — and how to not lie to yourself
**⚠️ The probe is part of the measurement, and most bad scope readings are probe errors.**
- **Compensate your 10× probe** against the scope's calibration output ⚠️ **every time you
  move it to a different channel or scope** — an uncompensated probe distorts edges and
  you will chase a phantom.
- **⚠️ The ground lead is an inductor.** That long crocodile clip forms a loop with the
  probe tip and **rings on every fast edge** — producing overshoot that isn't in your
  circuit. **For anything fast, use the spring ground tip.** This single habit removes a
  large share of imaginary signal-integrity problems.
- **10× probe** reduces loading (10 MΩ, ~10 pF) at the cost of amplitude —
  ⚠️ **1× loading (1 MΩ, ~100 pF) is enough to change a fast circuit's behaviour.**
- **Bandwidth**: ⚠️ **you need roughly 3–5× the signal's knee frequency** to see edges
  faithfully. A 100 MHz scope shows a 100 MHz square wave as a sine.
- **Sample rate ≥ 5× bandwidth**; watch for **aliasing** on repetitive signals.
- **Triggering** is the skill: edge, pulse-width, and ⚠️ **runt/glitch triggers are how
  you catch the intermittent event you're actually hunting.**
- **⚠️ Scope ground is usually mains earth** — **connecting it to a non-isolated hot node
  creates a short through the earth path** (§14). **Use a differential probe or an
  isolated scope.**

### 12.3 Other instruments
**Logic analyzer** — ⚠️ **the right tool for protocol debugging; a cheap 8-channel unit
with a protocol decoder is one of the best value purchases in the field.**
**Bench supply** — ⚠️ **current limiting is the feature that matters. Set it before you
power a new board and it will save hardware.**
**Function generator**, **spectrum analyzer**, **LCR meter**, **thermal camera**
(⚠️ **finds the hot part instantly — brilliant for locating a short**), **microscope**.

---
