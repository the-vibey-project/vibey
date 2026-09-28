---
id: skill-4-mosfet-switching-behaviour-8ebb7e8ce9
purpose: 4 mosfet switching behaviour
source: src/vibey_tools/skills/plugins/digital-logic-and-firmware-engineering/skills/logic-devices-transistors-cmos-gates-and-power/SKILL.md
requires: ["skill-3-transistors-as-switches-30fe96797c"]
links: ["skill-5-static-cmos-gates-adb0daf92c"]
---

## §4. MOSFET Switching Behaviour

**⚠️ The parasitic capacitances are the whole story of speed**: ⚠️ **gate capacitance must
be charged and discharged to switch the device, and everything a gate drives is capacitance
to the driver.**
**⚠️ Propagation delay** is therefore ⚠️ **roughly the load capacitance divided by the
available drive current — which is why delay depends on FANOUT and on wire length.**
**⚠️ Rise and fall times** and ⚠️ **the danger of slow edges: a slowly-transitioning input
leaves BOTH transistors in the receiving gate partially on, causing SHORT-CIRCUIT current
(§8) and, at the extreme, oscillation.**
**⚠️ The Miller effect** — ⚠️ **gate-drain capacitance appears amplified during the
transition, which is why the switching waveform has a plateau.**
**⚠️ Threshold voltage, body effect, and temperature dependence** — ⚠️ **and the
uncomfortable fact that transistors get SLOWER hot but LEAKIER hot, so the worst case for
timing and the worst case for power are at opposite corners.**
**⚠️ PVT corners** (process, voltage, temperature) — ⚠️ **designs must work at all of them,
which is why sign-off is done at multiple corners rather than nominal.**

---

# PART II — CMOS CIRCUIT DESIGN
