---
id: skill-4-the-mosfet-f091f95f35
purpose: 4 the mosfet
source: src/vibey_tools/skills/plugins/semiconductors-and-chip-manufacturing/skills/semi-carriers-doping-junctions-mosfet-and-scaling/SKILL.md
requires: ["skill-3-junctions-and-contacts-4a24334306"]
links: ["skill-5-scaling-and-what-ended-507ff30d91"]
---

## §4. The MOSFET

```
⚠️ THE STRUCTURE  source, drain, channel, gate separated by a
   thin gate DIELECTRIC
⚠️ OPERATION  gate voltage creates a field that INVERTS the channel
   surface, forming a conducting path. ⚠️ It is a voltage-controlled
   switch with essentially no DC gate current — which is why CMOS
   scales and bipolar didn't
⚠️ CMOS  complementary n and p devices. ⚠️ Static power is
   near zero because one device is always off — ⚠️ this property
   is why CMOS won, and why leakage breaking it (§5) was such a
   crisis
⚠️ THE KEY PARAMETERS
   ⚠️ THRESHOLD VOLTAGE Vt · drive current Ion · ⚠️ LEAKAGE Ioff ·
   ⚠️ SUBTHRESHOLD SWING — ⚠️ how many millivolts of gate voltage
   are needed per decade of current change. ⚠️ IT HAS A HARD
   PHYSICAL FLOOR OF ABOUT 60 mV/decade AT ROOM TEMPERATURE,
   set by Boltzmann statistics. ⚠️ THIS FLOOR IS WHY SUPPLY
   VOLTAGE STOPPED SCALING (§5)
⚠️ SHORT CHANNEL EFFECTS  ⚠️ as the channel shortens, the drain
   starts competing with the gate for control — DIBL, punchthrough,
   Vt roll-off. ⚠️ Fighting this is what drove FinFET and GAA (§6)
```

---
