---
id: skill-8-the-diesel-cycle-compression-ignition-ef289f5eb4
purpose: 8 the diesel cycle compression ignition
source: src/vibey_tools/skills/plugins/engines-generators-and-fuels/skills/engines-otto-diesel-brayton-stirling-and-combined-cycles/SKILL.md
requires: ["skill-7-the-otto-cycle-spark-ignition-petrol-2dbdd53aa8"]
links: ["skill-9-the-brayton-cycle-gas-turbines-4bd0c47f5a"]
---

## §8 The Diesel cycle (compression-ignition)

Diesels compress air to such a high temperature (**typically 700–900°C at TDC**) that injected fuel
ignites spontaneously — **no spark plug**. This requires much higher compression ratios, which is why
diesels are inherently more efficient.

| | Petrol (Otto) | Diesel |
|---|---|---|
| Ignition | Spark | Compression |
| Compression ratio | 8:1 to 13:1 | **14:1 to 25:1** |
| Throttle | Yes — pumping losses | **None** — power controlled by fuel quantity, not air, so pumping losses are lower |
| Injection | — | Very high pressures; common-rail at **2,000+ bar** |
| Cold start aid | — | Glow plugs |
| Road engine | 25–35% | **35–45%** |
| Large marine | — | **50–55% — the highest of any internal combustion engine** |

**Diagnostic consequence:** because ignition is by compression, a diesel "misfire" is **always a
fuelling or compression problem, never an ignition one**.

**Why lean running forces DPF and SCR rather than a three-way catalyst.** Diesels run lean overall, so
a three-way catalyst cannot work — there is excess oxygen in the exhaust, and a three-way catalyst
only works at stoichiometric operation (§17 → `engines-fuels-and-combustion`). Diesel aftertreatment
therefore requires two devices instead:

| Device | Target | Mechanism |
|---|---|---|
| **DPF** (diesel particulate filter) | Soot | Traps soot and **periodically regenerates by burning it off at high temperature** |
| **SCR** (selective catalytic reduction) | NOx | Uses **urea/AdBlue to convert NOx to nitrogen and water** |
