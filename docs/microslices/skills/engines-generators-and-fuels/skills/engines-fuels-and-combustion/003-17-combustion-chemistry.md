---
id: skill-17-combustion-chemistry-9f8285b0b5
purpose: 17 combustion chemistry
source: src/vibey_tools/skills/plugins/engines-generators-and-fuels/skills/engines-fuels-and-combustion/SKILL.md
requires: ["skill-16-the-fuel-comparison-table-1e7ce1d531"]
links: []
---

## §17 Combustion chemistry

**Stoichiometric air-fuel ratio.**

| Fuel | Stoichiometric AFR (by mass) | How it is actually run |
|---|---|---|
| Petrol | **about 14.7:1** (1 kg fuel needs 14.7 kg air) | Held at stoichiometric by closed-loop control |
| Diesel | **about 14.5:1** | Typically **lean, 20:1 to 60:1**, because power is controlled by fuel quantity, not air |

**The equivalence ratio φ.** **φ > 1 is rich** (excess fuel); **φ < 1 is lean** (excess air).

**The rich/lean trade-off — there is no free side.**

| | Power | Efficiency | Emissions |
|---|---|---|---|
| **Rich (φ > 1)** | More power | Lower efficiency | Higher CO / HC |
| **Lean (φ < 1)** | Less power | More efficient | **More NOx** — peak flame temperatures are high with excess oxygen |

**Why closed-loop fuel control exists.** Modern engines use **three-way catalysts, which require
stoichiometric operation** — the converter only works inside a narrow window around φ = 1. That constraint,
not fuel economy, is what forces the engine to hold stoichiometric continuously, and it is the whole reason
for the O₂-sensor feedback loop and fuel trims described in §18–§20 →
`engines-rebuilding-engines-materials-and-tolerances`. The same chemistry explains a structural asymmetry
between the two engine families: **diesels run lean overall, so a three-way catalyst cannot work** (excess
oxygen in the exhaust), which is why diesel aftertreatment takes the entirely different DPF-plus-SCR route
covered in §7–§11 → `engines-otto-diesel-brayton-stirling-and-combined-cycles`.

> **Fuel handling is a safety subject, not a logistics one.** Flash points, vapour pooling, storage siting,
> extinguisher selection and fuel-supply shutoff are covered in full in §21–§23 → `engines-safety-and-reference`.
> Read it before storing any quantity of fuel.
