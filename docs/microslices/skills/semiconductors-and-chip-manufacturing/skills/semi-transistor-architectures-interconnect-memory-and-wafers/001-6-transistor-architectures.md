---
id: skill-6-transistor-architectures-a07aa81560
purpose: 6 transistor architectures
source: src/vibey_tools/skills/plugins/semiconductors-and-chip-manufacturing/skills/semi-transistor-architectures-interconnect-memory-and-wafers/SKILL.md
requires: []
links: ["skill-7-interconnect-4968b8a435"]
---

## §6. Transistor Architectures

```
⚠️ PLANAR  gate controls the channel from one side. ⚠️ Ran out of
   electrostatic control around 28–22nm
⚠️ FinFET  ⚠️ the channel is a vertical fin, gated on three sides.
   ⚠️ Vastly better control, and it bought roughly a decade.
   ⚠️ Note the quantization: you get integer numbers of fins,
   so drive strength comes in steps
⚠️ GAA / NANOSHEET (RibbonFET at Intel)  ⚠️ the gate wraps the
   channel COMPLETELY — stacked horizontal sheets. ⚠️ Best
   electrostatics, and ⚠️ sheet WIDTH is continuously tunable,
   restoring analog drive-strength control. ⚠️ This is the 2nm-class
   generation now in production
⚠️ CFET (complementary FET)  ⚠️ stack the n and p devices
   VERTICALLY on top of each other. Research/early development —
   the next major architectural step
⚠️ BACKSIDE POWER DELIVERY (PowerVia at Intel, Super Power Rail
   at TSMC)  ⚠️ move power routing to the WAFER BACKSIDE, freeing
   the front side entirely for signal. ⚠️ Reduces IR drop and
   routing congestion — one of the genuinely significant recent
   changes, and separate from the transistor itself
⚠️ STRAIN, high-k/metal gate, and SiGe channels are the materials
   levers used alongside the geometry
```

---
