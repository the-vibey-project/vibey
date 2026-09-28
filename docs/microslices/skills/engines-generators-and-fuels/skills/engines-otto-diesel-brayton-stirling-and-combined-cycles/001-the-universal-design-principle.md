---
id: skill-the-universal-design-principle-923b2c19ec
purpose: the universal design principle
source: src/vibey_tools/skills/plugins/engines-generators-and-fuels/skills/engines-otto-diesel-brayton-stirling-and-combined-cycles/SKILL.md
requires: []
links: ["skill-7-the-otto-cycle-spark-ignition-petrol-2dbdd53aa8"]
---

## THE UNIVERSAL DESIGN PRINCIPLE

All heat engines descend from the same ancestor: heat flows from hot to cold, and you can extract work
from that flow if you insert a machine in the path. Engine types are distinguished by working fluid,
thermodynamic cycle, internal or external combustion, and batch (reciprocating) or continuous (rotary)
operation.

> **Every improvement to every engine cycle is the same idea in different clothes — move heat addition
> to a HIGHER average temperature, or heat rejection to a LOWER one.** Superheating, reheating,
> regeneration, intercooling, combined cycles, higher compression ratios all serve that single goal.

That is the Carnot ceiling η = 1 − T_C/T_H (§2 → `engines-thermodynamics-and-the-carnot-ceiling`)
expressed as design practice. Read every cycle below as an answer to one question: *where is the lever
on T_H or T_C, and what stops me pulling it further?*

| Cycle | Combustion / flow | Lever on T_H | What stops you | Real efficiency |
|---|---|---|---|---|
| Otto (§7) | Internal, batch | Compression ratio | Knock — a fuel-chemistry limit | 25–35% |
| Diesel (§8) | Internal, batch | Much higher compression ratio | Peak cylinder pressure, mechanical stress, NOx emissions | 35–45% road; **50–55% large marine** |
| Brayton (§9) | Internal, continuous | Turbine firing temperature | Back-work ratio; blade materials | 30–40% simple cycle |
| Stirling (§10) | External, batch, sealed fluid | Any external heat source | Heat transfer, sealing, regenerator | Carnot in theory only |
| Combined (§11) | Brayton topping + Rankine bottoming | Brayton T_H with Rankine T_C | Nothing better is in service | **55–62%** |
