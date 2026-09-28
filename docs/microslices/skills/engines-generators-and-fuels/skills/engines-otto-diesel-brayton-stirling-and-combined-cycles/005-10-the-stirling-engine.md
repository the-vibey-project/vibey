---
id: skill-10-the-stirling-engine-a56dc9dc14
purpose: 10 the stirling engine
source: src/vibey_tools/skills/plugins/engines-generators-and-fuels/skills/engines-otto-diesel-brayton-stirling-and-combined-cycles/SKILL.md
requires: ["skill-9-the-brayton-cycle-gas-turbines-4bd0c47f5a"]
links: ["skill-11-the-combined-cycle-the-most-efficient-heat-engine-6eae416797"]
---

## §10 The Stirling engine

**External combustion with a sealed working fluid** (usually air, helium, or hydrogen). Heat is
applied from outside to one end and removed from the other. A **displacer piston** shuttles the fluid
between hot and cold spaces through a **regenerator** — a heat store that saves heat between cycles —
and expansion and contraction drive a **power piston**.

**Why it can theoretically reach Carnot:** heat addition and rejection are **isothermal**, the Carnot
cycle's defining feature.

**The three practical limits:**

| # | Limit | Why it bites |
|---|---|---|
| 1 | Heat transfer rates through cylinder walls | Slow — the isothermal ideal assumes heat moves as fast as the piston |
| 2 | Sealing of the working fluid | **Hydrogen and helium leak through almost anything** |
| 3 | Regenerator size | The heat store must be large to save heat between cycles |

Low power density and slow response to load changes are the *consequence* of those three, and are
what has limited Stirling engines to niche applications.

**What they are good at:** quiet; can use **any heat source** (solar, geothermal, biomass, waste
heat); **no exhaust emissions from the cycle itself**. External combustion leaves the fuel question
wide open (§15–§17 → `engines-fuels-and-combustion`).
