---
id: skill-9-the-brayton-cycle-gas-turbines-4bd0c47f5a
purpose: 9 the brayton cycle gas turbines
source: src/vibey_tools/skills/plugins/engines-generators-and-fuels/skills/engines-otto-diesel-brayton-stirling-and-combined-cycles/SKILL.md
requires: ["skill-8-the-diesel-cycle-compression-ignition-ef289f5eb4"]
links: ["skill-10-the-stirling-engine-a56dc9dc14"]
---

## §9 The Brayton cycle (gas turbines)

Powers jet engines, gas turbine power plants, and the turboshafts of helicopters and some ships.
**Continuous flow, continuous combustion, no reciprocating parts.** Three steps: **compress** ambient
air; **burn** fuel continuously at constant pressure; **expand** the hot gases through a turbine. Some
turbine output drives the compressor; the rest is useful output.

### The back-work ratio problem

> The compressor typically consumes **50–65% of the turbine's gross output** — the Brayton cycle's
> fundamental disadvantage against Rankine, because compressing gas is expensive.

**Isentropic compressor efficiency is critical: compressor irreversibility hurts more than turbine
irreversibility, because the compressor consumes such a large fraction of output.** Contrast Rankine,
where pump work is typically only 1–2% of turbine work because liquid water is nearly incompressible
(§4 → `engines-rankine-steam-engines-and-turbines`) — that low back-work ratio is Rankine's advantage.

| Improvement | What it does | Which side of the principle |
|---|---|---|
| **Intercooling** | Cool between compressor stages to reduce work | Attacks the back-work ratio |
| **Reheat** | Add heat between turbine stages | Raises average heat-addition temperature |
| **Regeneration** | Turbine exhaust preheats compressed air before combustion | Recycles rejected heat into heat addition |
| **Combined cycle (§11)** | Bottoming Rankine cycle on the exhaust | **The biggest step by far** |

Efficiency: simple-cycle gas turbines **30–40%**; combined-cycle plants **55–62%**, the highest of any
heat engine in commercial service. First-stage blades run in 1400–1600°C gas and survive only via
internal cooling, thermal barrier coatings and single-crystal casting
(§20 → `engines-rebuilding-engines-materials-and-tolerances`) — the materials constraint behind the
Carnot lever.
